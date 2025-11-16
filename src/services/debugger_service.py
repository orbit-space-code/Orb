"""
Advanced debugger service for Orb with support for breakpoints, variable inspection,
and step-by-step execution.
"""
import ast
import sys
import asyncio
import inspect
import traceback
from typing import Dict, List, Optional, Any, Callable, Union
from enum import Enum, auto
from dataclasses import dataclass

class DebuggerState(Enum):
    READY = auto()
    RUNNING = auto()
    PAUSED = auto()
    STEPPING = auto()
    FINISHED = auto()
    ERROR = auto()

@dataclass
class DebuggerEvent:
    """Represents a debugger event"""
    event_type: str
    data: Dict[str, Any] = None

class Breakpoint:
    """Represents a breakpoint in the code"""
    def __init__(self, file_path: str, line_number: int, condition: str = None):
        self.file_path = file_path
        self.line_number = line_number
        self.condition = condition
        self.hit_count = 0
        self.enabled = True

class Debugger:
    """Advanced debugger with breakpoint and stepping support"""
    
    def __init__(self):
        self.state = DebuggerState.READY
        self.breakpoints: Dict[str, List[Breakpoint]] = {}
        self.variables: Dict[str, Dict[str, Any]] = {}
        self.call_stack = []
        self._output_buffer = []
        self._original_trace = None
        self._current_frame = None
        self._stop_requested = False
        self._continue_signal = asyncio.Event()
        self._step_signal = asyncio.Event()
        self._event_handlers = {}
        
    def add_event_handler(self, event_type: str, handler: Callable[[DebuggerEvent], None]):
        """Register an event handler"""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)
        
    def _emit_event(self, event: DebuggerEvent):
        """Emit an event to all registered handlers"""
        for handler in self._event_handlers.get(event.event_type, []):
            try:
                handler(event)
            except Exception as e:
                print(f"Error in event handler: {e}", file=sys.stderr)
    
    def add_breakpoint(self, file_path: str, line_number: int, condition: str = None) -> Breakpoint:
        """Add a breakpoint at the specified location"""
        if file_path not in self.breakpoints:
            self.breakpoints[file_path] = []
            
        bp = Breakpoint(file_path, line_number, condition)
        self.breakpoints[file_path].append(bp)
        return bp
        
    def remove_breakpoint(self, file_path: str, line_number: int) -> bool:
        """Remove a breakpoint"""
        if file_path not in self.breakpoints:
            return False
            
        initial_count = len(self.breakpoints[file_path])
        self.breakpoints[file_path] = [
            bp for bp in self.breakpoints[file_path] 
            if bp.line_number != line_number
        ]
        return len(self.breakpoints[file_path]) < initial_count
    
    def get_variables(self, frame=None) -> Dict[str, Any]:
        """Get variables in the current or specified frame"""
        if frame is None:
            frame = self._current_frame
            if frame is None:
                return {}
                
        variables = {}
        # Get local variables
        variables.update(frame.f_locals)
        # Get global variables
        variables.update({
            k: v for k, v in frame.f_globals.items()
            if not (k.startswith('__') and k.endswith('__'))
        })
        return variables
    
    def _should_break(self, frame, event, arg):
        """Determine if execution should pause at the current line"""
        if self.state == DebuggerState.STEPPING:
            self.state = DebuggerState.PAUSED
            return True
            
        if event != 'line' or frame.f_code.co_filename == '<string>':
            return False
            
        # Check for breakpoints
        file_breakpoints = self.breakpoints.get(frame.f_code.co_filename, [])
        for bp in file_breakpoints:
            if (bp.enabled and bp.line_number == frame.f_lineno and 
                (bp.condition is None or eval(bp.condition, frame.f_globals, frame.f_locals))):
                bp.hit_count += 1
                self._current_frame = frame
                return True
                
        return False
    
    def trace_dispatch(self, frame, event, arg):
        """Trace function for the debugger"""
        if self._stop_requested:
            return None
            
        if event == 'call':
            self.call_stack.append(frame)
            if self.state == DebuggerState.STEPPING:
                self.state = DebuggerState.PAUSED
                return self.trace_dispatch
                
        elif event == 'line' and self._should_break(frame, event, arg):
            self.state = DebuggerState.PAUSED
            self._current_frame = frame
            self._emit_event(DebuggerEvent("breakpoint_hit", {
                "file": frame.f_code.co_filename,
                "line": frame.f_lineno,
                "variables": self.get_variables(frame)
            }))
            return self.trace_dispatch
            
        elif event == 'return':
            if self.call_stack and self.call_stack[-1] == frame:
                self.call_stack.pop()
                
        return self.trace_dispatch
    
    async def execute_code(self, code: str, globals_dict: Optional[Dict] = None, 
                         locals_dict: Optional[Dict] = None) -> str:
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
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        sys.stdout = sys.stderr = self._output_buffer = []
        
        try:
            # Parse the code to insert debugger calls
            tree = ast.parse(code)
            self._instrument_ast(tree)
            
            # Compile and execute the instrumented code
            code_obj = compile(tree, filename="<string>", mode="exec")
            
            # Set up tracing
            self._original_trace = sys.gettrace()
            sys.settrace(self.trace_dispatch)
            
            # Run in a separate task to allow for async debugging
            task = asyncio.create_task(self._run_code(code_obj, globals_dict, locals_dict))
            
            # Main debug loop
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
                
            # Clean up if we're stopping
            if self._stop_requested and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                    
            # Get the output
            output = "\n".join(str(line) for line in self._output_buffer)
            return output
            
        except Exception as e:
            self.state = DebuggerState.ERROR
            self._emit_event(DebuggerEvent("error", {
                "error": str(e), 
                "traceback": traceback.format_exc()
            }))
            raise
            
        finally:
            # Clean up
            if self._original_trace is not None:
                sys.settrace(self._original_trace)
            sys.stdout = original_stdout
            sys.stderr = original_stderr
            self.state = DebuggerState.FINISHED
            self._emit_event(DebuggerEvent("finished"))
    
    def _instrument_ast(self, node):
        """Instrument the AST to add debugging support"""
        for field, old_value in ast.iter_fields(node):
            if isinstance(old_value, list):
                new_values = []
                for value in old_value:
                    if isinstance(value, ast.AST):
                        value = self._instrument_node(value)
                        if value is not None:
                            new_values.append(value)
                    else:
                        new_values.append(value)
                old_value[:] = new_values
            elif isinstance(old_value, ast.AST):
                new_node = self._instrument_node(old_value)
                if new_node is None:
                    delattr(node, field)
                else:
                    setattr(node, field, new_node)
    
    def _instrument_node(self, node):
        """Instrument a single AST node for debugging"""
        self._instrument_ast(node)
        
        # Add debugging for function definitions
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Add entry/exit tracing
            entry_call = ast.Expr(
                value=ast.Call(
                    func=ast.Name(id='__debugger__._on_function_entry', ctx=ast.Load()),
                    args=[ast.Str(s=node.name)],
                    keywords=[]
                )
            )
            
            # Add a try/finally to ensure we trace function exit
            if node.body:
                try_body = node.body
            else:
                try_body = [ast.Pass()]
                
            # Create the function exit handler
            exit_call = ast.Expr(
                value=ast.Call(
                    func=ast.Name(id='__debugger__._on_function_exit', ctx=ast.Load()),
                    args=[ast.Str(s=node.name)],
                    keywords=[]
                )
            )
            
            # Wrap the function body in try/finally
            node.body = [
                entry_call,
                ast.Try(
                    body=try_body,
                    handlers=[],
                    orelse=[],
                    finalbody=[exit_call]
                )
            ]
            
        return node
    
    def _on_function_entry(self, func_name):
        """Called when entering a function"""
        frame = inspect.currentframe().f_back
        self._emit_event(DebuggerEvent("function_entry", {
            "name": func_name,
            "args": {k: v for k, v in frame.f_locals.items() 
                    if k != 'self' and not k.startswith('_')}
        }))
    
    def _on_function_exit(self, func_name):
        """Called when exiting a function"""
        self._emit_event(DebuggerEvent("function_exit", {
            "name": func_name
        }))
    
    async def _run_code(self, code_obj, globals_dict, locals_dict):
        """Run code in an executor to avoid blocking the event loop"""
        loop = asyncio.get_running_loop()
        
        def _exec():
            try:
                exec(code_obj, globals_dict, locals_dict)
            except Exception as e:
                self.state = DebuggerState.ERROR
                self._emit_event(DebuggerEvent("error", {
                    "error": str(e),
                    "traceback": traceback.format_exc()
                }))
        
        await loop.run_in_executor(None, _exec)
    
    # Debugger control methods
    def pause(self):
        """Pause execution at the next opportunity"""
        if self.state == DebuggerState.RUNNING:
            self.state = DebuggerState.PAUSED
    
    def continue_execution(self):
        """Continue execution until the next breakpoint"""
        if self.state == DebuggerState.PAUSED:
            self._continue_signal.set()
    
    def step_over(self):
        """Step over the current line"""
        if self.state == DebuggerState.PAUSED:
            self._step_signal.set()
    
    def step_into(self):
        """Step into the current function call"""
        if self.state == DebuggerState.PAUSED:
            self.state = DebuggerState.STEPPING
            self._continue_signal.set()
    
    def step_out(self):
        """Step out of the current function"""
        if self.state == DebuggerState.PAUSED:
            # For simplicity, we'll just continue to the next return
            self.state = DebuggerState.STEPPING
            self._continue_signal.set()
    
    def stop(self):
        """Stop debugging"""
        self._stop_requested = True
        self.state = DebuggerState.FINISHED
        self._continue_signal.set()

# Example usage
async def example():
    debugger = Debugger()
    
    def on_breakpoint(event):
        print(f"Breakpoint hit at {event.data['file']}:{event.data['line']}")
        print("Variables:", event.data['variables'])
    
    debugger.add_event_handler("breakpoint_hit", on_breakpoint)
    
    # Add a breakpoint
    debugger.add_breakpoint("<string>", 5)  # Break on line 5
    
    # Example code to debug
    code = """
x = 1
y = 2
for i in range(3):
    z = x + y + i  # This is line 5
    print(z)
"""
    
    # Run the code with the debugger
    await debugger.execute_code(code)

if __name__ == "__main__":
    asyncio.run(example())
