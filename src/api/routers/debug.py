"""
Debugger API endpoints for the Orb IDE
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from typing import Dict, List, Optional
import json
import asyncio
from ...services.debugger_service import Debugger, DebuggerState, Breakpoint

router = APIRouter(prefix="/debug", tags=["debug"])

class ConnectionManager:
    """Manages WebSocket connections for the debugger UI"""
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.debugger = Debugger()
        self._setup_debugger_handlers()
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
    async def send_message(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)
    
    def _setup_debugger_handlers(self):
        """Set up debugger event handlers"""
        self.debugger.add_event_handler("breakpoint_hit", self._on_breakpoint_hit)
        self.debugger.add_event_handler("function_entry", self._on_function_entry)
        self.debugger.add_event_handler("function_exit", self._on_function_exit)
        self.debugger.add_event_handler("error", self._on_error)
        self.debugger.add_event_handler("finished", self._on_finished)
    
    async def _on_breakpoint_hit(self, event):
        await self.broadcast({
            "type": "breakpoint_hit",
            "data": event.data
        })
    
    async def _on_function_entry(self, event):
        await self.broadcast({
            "type": "function_entry",
            "data": event.data
        })
    
    async def _on_function_exit(self, event):
        await self.broadcast({
            "type": "function_exit",
            "data": event.data
        })
    
    async def _on_error(self, event):
        await self.broadcast({
            "type": "error",
            "data": event.data
        })
    
    async def _on_finished(self, event):
        await self.broadcast({
            "type": "finished",
            "data": {}
        })

manager = ConnectionManager()

@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            await handle_message(message, websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

async def handle_message(message: dict, websocket: WebSocket):
    """Handle incoming WebSocket messages"""
    msg_type = message.get("type")
    data = message.get("data", {})
    
    if msg_type == "add_breakpoint":
        await handle_add_breakpoint(data, websocket)
    elif msg_type == "remove_breakpoint":
        await handle_remove_breakpoint(data, websocket)
    elif msg_type == "step_over":
        manager.debugger.step_over()
    elif msg_type == "step_into":
        manager.debugger.step_into()
    elif msg_type == "step_out":
        manager.debugger.step_out()
    elif msg_type == "continue_execution":
        manager.debugger.continue_execution()
    elif msg_type == "pause":
        manager.debugger.pause()
    elif msg_type == "stop":
        manager.debugger.stop()
    elif msg_type == "evaluate":
        await handle_evaluate(data, websocket)
    elif msg_type == "add_watch":
        await handle_add_watch(data, websocket)
    elif msg_type == "remove_watch":
        await handle_remove_watch(data, websocket)

async def handle_add_breakpoint(data: dict, websocket: WebSocket):
    """Handle adding a breakpoint"""
    file_path = data.get("filePath")
    line_number = data.get("lineNumber")
    condition = data.get("condition")
    
    if file_path and line_number is not None:
        bp = manager.debugger.add_breakpoint(file_path, line_number, condition)
        await manager.send_message({
            "type": "breakpoint_added",
            "data": {
                "id": id(bp),
                "filePath": file_path,
                "lineNumber": line_number,
                "condition": condition
            }
        }, websocket)

async def handle_remove_breakpoint(data: dict, websocket: WebSocket):
    """Handle removing a breakpoint"""
    file_path = data.get("filePath")
    line_number = data.get("lineNumber")
    
    if file_path and line_number is not None:
        removed = manager.debugger.remove_breakpoint(file_path, line_number)
        await manager.send_message({
            "type": "breakpoint_removed",
            "data": {
                "filePath": file_path,
                "lineNumber": line_number,
                "success": removed
            }
        }, websocket)

async def handle_evaluate(data: dict, websocket: WebSocket):
    """Handle expression evaluation"""
    expression = data.get("expression")
    frame = manager.debugger._current_frame
    
    if not expression or not frame:
        return
    
    try:
        # Evaluate the expression in the current frame's context
        result = eval(expression, frame.f_globals, frame.f_locals)
        await manager.send_message({
            "type": "evaluation_result",
            "data": {
                "expression": expression,
                "result": str(result),
                "type": type(result).__name__
            }
        }, websocket)
    except Exception as e:
        await manager.send_message({
            "type": "evaluation_error",
            "data": {
                "expression": expression,
                "error": str(e)
            }
        }, websocket)

async def handle_add_watch(data: dict, websocket: WebSocket):
    """Handle adding a watch expression"""
    expression = data.get("expression")
    if not expression:
        return
    
    # In a real implementation, you'd store this in a database
    watch_id = f"watch_{len(manager.debugger.watch_expressions) + 1}"
    manager.debugger.watch_expressions[watch_id] = expression
    
    await manager.send_message({
        "type": "watch_added",
        "data": {
            "id": watch_id,
            "expression": expression
        }
    }, websocket)

async def handle_remove_watch(data: dict, websocket: WebSocket):
    """Handle removing a watch expression"""
    watch_id = data.get("id")
    if watch_id in manager.debugger.watch_expressions:
        del manager.debugger.watch_expressions[watch_id]
        
    await manager.send_message({
        "type": "watch_removed",
        "data": {
            "id": watch_id
        }
    }, websocket)

# Add watch expressions support to the Debugger class
if not hasattr(Debugger, 'watch_expressions'):
    Debugger.watch_expressions = {}

def get_debugger_ui():
    """Return the HTML for the debugger UI"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Orb Debugger</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 0; display: flex; height: 100vh; }
            #sidebar { width: 300px; background: #f5f5f5; padding: 10px; border-right: 1px solid #ddd; }
            #main { flex: 1; display: flex; flex-direction: column; }
            #editor { flex: 1; border: 1px solid #ddd; margin: 10px; }
            #variables { height: 200px; overflow-y: auto; border: 1px solid #ddd; margin: 10px; }
            #console { height: 150px; overflow-y: auto; border: 1px solid #ddd; margin: 10px; padding: 5px; }
            .breakpoint { color: red; }
            .current-line { background-color: #ffffcc; }
            .toolbar { padding: 5px; background: #eee; border-bottom: 1px solid #ddd; }
            button { margin: 2px; }
            .variable { font-family: monospace; }
            .watch-expression { margin: 5px 0; }
        </style>
    </head>
    <body>
        <div id="sidebar">
            <h3>Breakpoints</h3>
            <div id="breakpoints"></div>
            <h3>Watch</h3>
            <div id="watch-expressions">
                <input type="text" id="watch-input" placeholder="Add watch expression">
                <button onclick="addWatch()">+</button>
                <div id="watches"></div>
            </div>
        </div>
        <div id="main">
            <div class="toolbar">
                <button onclick="stepOver()">Step Over</button>
                <button onclick="stepInto()">Step Into</button>
                <button onclick="stepOut()">Step Out</button>
                <button onclick="continueExecution()">Continue</button>
                <button onclick="pauseExecution()">Pause</button>
                <button onclick="stopDebugging()">Stop</button>
            </div>
            <div id="editor"></div>
            <div id="variables">
                <h3>Variables</h3>
                <div id="variables-content"></div>
            </div>
            <div id="console">
                <h3>Console</h3>
                <div id="console-content"></div>
            </div>
        </div>

        <script>
            const ws = new WebSocket(`ws://${window.location.host}/debug/ws/${Date.now()}`);
            let currentLine = -1;
            let editor;
            
            // Initialize CodeMirror editor
            document.addEventListener('DOMContentLoaded', () => {
                editor = CodeMirror(document.getElementById('editor'), {
                    lineNumbers: true,
                    mode: 'python',
                    theme: 'default',
                    lineWrapping: true,
                    gutters: ["breakpoints", "CodeMirror-linenumbers"],
                });
                
                // Handle breakpoint clicks
                editor.on("gutterClick", (cm, line) => {
                    const info = cm.lineInfo(line);
                    if (info.gutterMarkers) {
                        cm.setGutterMarker(line, "breakpoints", null);
                        removeBreakpoint(line + 1);
                    } else {
                        const marker = document.createElement("div");
                        marker.innerHTML = "●";
                        marker.style.color = "#ff0000";
                        cm.setGutterMarker(line, "breakpoints", marker);
                        addBreakpoint(line + 1);
                    }
                });
                
                // Load initial code
                fetch('/api/code')
                    .then(response => response.text())
                    .then(code => editor.setValue(code));
            });
            
            // WebSocket message handling
            ws.onmessage = (event) => {
                const message = JSON.parse(event.data);
                console.log('Message from server:', message);
                
                switch (message.type) {
                    case 'breakpoint_hit':
                        highlightLine(message.data.line - 1);
                        updateVariables(message.data.variables);
                        break;
                    case 'function_entry':
                        logToConsole(`→ Entering ${message.data.name}(${JSON.stringify(message.data.args)})`);
                        break;
                    case 'function_exit':
                        logToConsole(`← Exiting ${message.data.name}`);
                        break;
                    case 'error':
                        logToConsole(`ERROR: ${message.data.error}\n${message.data.traceback}`);
                        break;
                    case 'evaluation_result':
                        logToConsole(`${message.data.expression} = ${message.data.result} (${message.data.type})`);
                        break;
                    case 'evaluation_error':
                        logToConsole(`Error evaluating '${message.data.expression}': ${message.data.error}`);
                        break;
                }
            };
            
            // Debugger control functions
            function stepOver() { sendMessage({ type: 'step_over' }); }
            function stepInto() { sendMessage({ type: 'step_into' }); }
            function stepOut() { sendMessage({ type: 'step_out' }); }
            function continueExecution() { sendMessage({ type: 'continue_execution' }); }
            function pauseExecution() { sendMessage({ type: 'pause' }); }
            function stopDebugging() { sendMessage({ type: 'stop' }); }
            
            function addBreakpoint(line) {
                sendMessage({
                    type: 'add_breakpoint',
                    data: { filePath: 'current_file.py', lineNumber: line }
                });
            }
            
            function removeBreakpoint(line) {
                sendMessage({
                    type: 'remove_breakpoint',
                    data: { filePath: 'current_file.py', lineNumber: line }
                });
            }
            
            function addWatch() {
                const input = document.getElementById('watch-input');
                const expr = input.value.trim();
                if (expr) {
                    sendMessage({
                        type: 'add_watch',
                        data: { expression: expr }
                    });
                    input.value = '';
                }
            }
            
            function evaluateExpression(expr) {
                sendMessage({
                    type: 'evaluate',
                    data: { expression: expr }
                });
            }
            
            function sendMessage(message) {
                ws.send(JSON.stringify(message));
            }
            
            function highlightLine(line) {
                if (currentLine !== -1) {
                    editor.removeLineClass(currentLine, 'background', 'current-line');
                }
                currentLine = line;
                editor.addLineClass(line, 'background', 'current-line');
                editor.scrollIntoView({ line, ch: 0 }, 100);
            }
            
            function updateVariables(vars) {
                const container = document.getElementById('variables-content');
                container.innerHTML = '';
                
                for (const [name, value] of Object.entries(vars)) {
                    const div = document.createElement('div');
                    div.className = 'variable';
                    div.textContent = `${name} = ${value}`;
                    container.appendChild(div);
                }
            }
            
            function logToConsole(message) {
                const console = document.getElementById('console-content');
                const entry = document.createElement('div');
                entry.textContent = message;
                console.appendChild(entry);
                console.scrollTop = console.scrollHeight;
            }
        </script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.2/codemirror.min.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.2/mode/python/python.min.js"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.2/codemirror.min.css">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.2/theme/default.min.css">
    </body>
    </html>
    """

@router.get("/ui", response_class=HTMLResponse)
async def debugger_ui():
    """Serve the debugger UI"""
    return get_debugger_ui()
