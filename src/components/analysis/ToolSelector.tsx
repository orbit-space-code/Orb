'use client';

import { useState, useEffect } from 'react';

interface Tool {
  name: string;
  version: string;
  supported_languages: string[];
  supported_extensions: string[];
}

interface ToolSelectorProps {
  selectedTools: string[];
  onToolsChange: (tools: string[]) => void;
}

export default function ToolSelector({
  selectedTools,
  onToolsChange,
}: ToolSelectorProps) {
  const [tools, setTools] = useState<Tool[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchTools();
  }, []);

  const fetchTools = async () => {
    try {
      const fastApiUrl = process.env.NEXT_PUBLIC_FASTAPI_URL || 'http://localhost:8000';
      const response = await fetch(`${fastApiUrl}/analysis/tools`);
      const data = await response.json();
      setTools(data.tools);
    } catch (error) {
      console.error('Error fetching tools:', error);
    } finally {
      setLoading(false);
    }
  };

  const toggleTool = (toolName: string) => {
    if (selectedTools.includes(toolName)) {
      onToolsChange(selectedTools.filter((t) => t !== toolName));
    } else {
      onToolsChange([...selectedTools, toolName]);
    }
  };

  const selectAll = () => {
    onToolsChange(tools.map((t) => t.name));
  };

  const deselectAll = () => {
    onToolsChange([]);
  };

  if (loading) {
    return <div className="text-center py-4">Loading tools...</div>;
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold text-gray-900">Select Analysis Tools</h3>
        <div className="space-x-2">
          <button
            onClick={selectAll}
            className="text-sm text-indigo-600 hover:text-indigo-700"
          >
            Select All
          </button>
          <button
            onClick={deselectAll}
            className="text-sm text-gray-600 hover:text-gray-700"
          >
            Deselect All
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {tools.map((tool) => (
          <div
            key={tool.name}
            className={`border rounded-lg p-4 cursor-pointer transition-all ${
              selectedTools.includes(tool.name)
                ? 'border-indigo-500 bg-indigo-50'
                : 'border-gray-200 hover:border-gray-300'
            }`}
            onClick={() => toggleTool(tool.name)}
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <h4 className="font-semibold text-gray-900">{tool.name}</h4>
                <p className="text-sm text-gray-500">v{tool.version}</p>
                {tool.supported_languages.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {tool.supported_languages.map((lang) => (
                      <span
                        key={lang}
                        className="px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded"
                      >
                        {lang}
                      </span>
                    ))}
                  </div>
                )}
              </div>
              <input
                type="checkbox"
                checked={selectedTools.includes(tool.name)}
                onChange={() => {}}
                className="mt-1 h-5 w-5 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
              />
            </div>
          </div>
        ))}
      </div>

      <div className="text-sm text-gray-500">
        {selectedTools.length} tool{selectedTools.length !== 1 ? 's' : ''} selected
      </div>
    </div>
  );
}
