"""
Debugging Service
Provides debugging capabilities for code execution
"""
import asyncio
import inspect
import traceback
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import sys
import io
import contextlib
import ast
import astor

class DebuggerState(str, Enum):
    """Possible states of the debugger"""
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    STEPPING = "stepping"
    BREAKPOINT = "breakpoint"
    FINISHED = "finished"
    ERROR = "error"

@dataclass
class StackFrame:
    """Represents a stack frame in the debugger"""
    filename: str
    line: int
    function: str
    code_context: List[str] = field(default_factory=list)
    local_vars: Dict[str, Any] = field(default_factory=dict)
    global_vars: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Breakpoint:
    """Represents a breakpoint in the code"""
    id: str
    filename: str
    line: int
    condition: Optional[str] = None
    hit_count: int = 0
    enabled: bool = True

@dataclass
class DebuggerEvent:
    """Represents an event in the debugger"""
    type: str
    data: Dict[str, Any] = field(default_factory=dict)

class Debugger:
    """Interactive debugger for Python code"""
    
    def __init__(self):
        self.state = DebuggerState.READY
        self.breakpoints: Dict[str, Breakpoint] = {}
        self.call_stack: List[StackFrame] = []
        self.event_handlers: Dict[str, List[Callable]] = {}
        self._next_breakpoint_id = 1
        self._execution_paused = asyncio.Event()
        self._continue_signal = asyncio.Event()
        self._step_signal = asyncio.Event()
        self._stop_requested = False
        self._output_buffer = io.StringIO()
        self._original_stdout = None
        self._original_stderr = None
        
    def on(self, event_type: str, handler: Callable):
        """Register an event handler"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
        return self
    
    def _emit_event(self, event: DebuggerEvent):
        """Emit an event to all registered handlers"""
        for handler in self.event_handlers.get(event.type, []):
            try:
                handler(event)
            except Exception as e:
                print(f"Error in event handler: {e}", file=sys.stderr)
    
    async def execute_code(self, code: str, globals_dict: Optional[Dict] = None, locals_dict: Optional[Dict] = None):
        """Execute code with debugging support"""
        if self.state != DebuggerState.READY:
            raise RuntimeError("Debugger is already running")
            
        self.state = DebuggerState.RUNNING
        self._stop_requested = False
        
        # Set up execution context
        if globals_dict is None:
            globals_dict = {}
        if locals_dict is None:
            locals_dict = {}
            
        # Add debugger to globals
        globals_dict['__debugger__'] = self
        
        # Redirect stdout/stderr
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr
        sys.stdout = self._output_buffer
        sys.stderr = self._output_buffer
        
        try:
            # Parse the code to insert debugger calls
            tree = ast.parse(code)
            self._instrument_ast(tree)
            
            # Compile and execute the instrumented code
            code_obj = compile(tree, filename="<string>", mode="exec")
            
            # Run in a separate task to allow for async debugging
            task = asyncio.create_task(self._run_code(code_obj, globals_dict, locals_dict))
            
            # Wait for execution to complete or be paused
            while not task.done() and not self._stop_requested:
                if self.state == DebuggerState.PAUSED:
                    # Wait for continue or step signal
                    await asyncio.wait(
                        [self._continue_signal.wait(), self._step_signal.wait()],
                        return_when=asyncio.FIRST_COMPLETED
                    )
                    
                    if self._step_signal.is_set():
                        self._step_signal.clear()
                        self.state = DebuggerState.STEPPING
                        self._continue_signal.set()
                    elif self._continue_signal.is_set():
                        self._continue_signal.clear()
                        self.state = DebuggerState.RUNNING
                
                await asyncio.sleep(0.1)
                
            # If we're stopping, cancel the task
            if self._stop_requested and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                    
        except Exception as e:
            self.state = DebuggerState.ERROR
            self._emit_event(DebuggerEvent("error", {"error": str(e), "traceback": traceback.format_exc()}))
            raise
            
        finally:
            # Restore original stdout/stderr
            if self._original_stdout:
                sys.stdout = self._original_stdout
            if self._original_stderr:
                sys.stderr = self._original_stderr
                
            self.state = DebuggerState.FINISHED
            self._emit_event(DebuggerEvent("finished"))
    
    async def _run_code(self, code_obj, globals_dict, locals_dict):
        """Run the code in an async context"""
        try:
            exec(code_obj, globals_dict, locals_dict)
        except Exception as e:
            self.state = DebuggerState.ERROR
            self._emit_event(DebuggerEvent("error", {
                "error": str(e),
                "traceback": traceback.format_exc()
            }))
    
    def _instrument_ast(self, node):
        """Instrument the AST to add debugging support"""
        for field, old_value in ast.iter_fields(node):
            if isinstance(old_value, list):
                new_values = []
                for value in old_value:
                    if isinstance(value, ast.AST):
                        value = self._instrument_node(value)
                        if value is not None:
                            if not isinstance(value, list):
                                new_values.append(value)
                            else:
                                new_values.extend(value)
                    else:
                        new_values.append(value)
                old_value[:] = new_values
            elif isinstance(old_value, ast.AST):
                new_node = self._instrument_node(old_value)
                if new_node is not None:
                    setattr(node, field, new_node)
    
    def _instrument_node(self, node):
        """Instrument a single AST node"""
        self._instrument_ast(node)
        
        # Add debugger calls before statements
        if isinstance(node, (ast.stmt, ast.Expression)) and not isinstance(node, ast.Pass):
            # Create a debugger call
            debug_call = ast.Expr(
                value=ast.Call(
                    func=ast.Name(id='__debugger__', ctx=ast.Load()),
                    args=[ast.Str(s='line')],
                    keywords=[
                        ast.keyword(arg='filename', value=ast.Str(s=node.lineno)),
                        ast.keyword(arg='line', value=ast.Num(n=node.lineno if hasattr(node, 'lineno') else 0)),
                        ast.keyword(arg='event', value=ast.Str(s='line'))
                    ]
                )
            )
            
            # For function definitions, add a breakpoint at the start
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                return [
                    debug_call,
                    node
                ]
                
            return debug_call, node
            
        return node
    
    async def set_breakpoint(self, filename: str, line: int, condition: Optional[str] = None) -> Breakpoint:
        """Set a breakpoint at the specified location"""
        bp_id = f"bp_{self._next_breakpoint_id}"
        self._next_breakpoint_id += 1
        
        bp = Breakpoint(
            id=bp_id,
            filename=filename,
            line=line,
            condition=condition
        )
        
        self.breakpoints[bp_id] = bp
        self._emit_event(DebuggerEvent("breakpoint_added", {"breakpoint": bp}))
        return bp
    
    async def remove_breakpoint(self, breakpoint_id: str) -> bool:
        """Remove a breakpoint by ID"""
        if breakpoint_id in self.breakpoints:
            del self.breakpoints[breakpoint_id]
            self._emit_event(DebuggerEvent("breakpoint_removed", {"breakpoint_id": breakpoint_id}))
            return True
        return False
    
    async def continue_execution(self):
        """Continue execution until the next breakpoint"""
        if self.state == DebuggerState.PAUSED:
            self._continue_signal.set()
    
    async def step_over(self):
        """Step over the current line"""
        if self.state == DebuggerState.PAUSED:
            self._step_signal.set()
    
    async def step_into(self):
        """Step into the current function call"""
        if self.state == DebuggerState.PAUSED:
            # For simplicity, we'll treat step_into the same as step_over
            # A more complete implementation would track the call stack
            self._step_signal.set()
    
    async def step_out(self):
        """Step out of the current function"""
        if self.state == DebuggerState.PAUSED:
            # For simplicity, we'll treat step_out the same as continue
            self._continue_signal.set()
    
    async def pause_execution(self):
        """Pause execution at the next opportunity"""
        self.state = DebuggerState.PAUSED
        self._emit_event(DebuggerEvent("paused"))
    
    async def stop_execution(self):
        """Stop the current debugging session"""
        self._stop_requested = True
        self.state = DebuggerState.FINISHED
        self._emit_event(DebuggerEvent("stopped"))
    
    def get_variables(self, scope: str = "local") -> Dict[str, Any]:
        """Get variables from the current scope"""
        if not self.call_stack:
            return {}
            
        frame = self.call_stack[-1]
        if scope == "local":
            return frame.local_vars
        elif scope == "global":
            return frame.global_vars
        else:
            return {**frame.global_vars, **frame.local_vars}
    
    def get_call_stack(self) -> List[StackFrame]:
        """Get the current call stack"""
        return self.call_stack.copy()

# Singleton instance
debugger = Debugger()
