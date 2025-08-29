import React, { useState, useEffect } from 'react';
import { X, CheckCircle, AlertCircle, Mail, Loader2 } from 'lucide-react';

interface ProgressData {
  type: 'progress' | 'completion';
  step: string;
  title: string;
  description: string;
  progress?: number;
  total?: number;
  sent?: number;
  failed?: number;
  status?: 'completed' | 'failed';
  result?: {
    total: number;
    sent: number;
    failed: number;
  };
}

interface TopProgressBarProps {
  searchId?: number;
  isVisible: boolean;
  onClose: () => void;
}

const TopProgressBar: React.FC<TopProgressBarProps> = ({
  searchId,
  isVisible,
  onClose
}) => {
  const [progress, setProgress] = useState<ProgressData | null>(null);
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [isComplete, setIsComplete] = useState(false);

  // WebSocket连接
  useEffect(() => {
    if (!isVisible || !searchId) {
      return;
    }

    const websocket = new WebSocket(`ws://127.0.0.1:8002/ws/batch_email_${searchId}`);
    
    websocket.onopen = () => {
      console.log('顶部进度条WebSocket连接已建立');
      setWs(websocket);
    };
    
    websocket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log('顶部进度条收到更新:', data);
        setProgress(data);
        
        if (data.type === 'completion') {
          setIsComplete(true);
          // 5秒后自动隐藏完成状态
          setTimeout(() => {
            onClose();
          }, 5000);
        }
      } catch (error) {
        console.error('解析WebSocket消息失败:', error);
      }
    };
    
    websocket.onclose = () => {
      console.log('顶部进度条WebSocket连接已关闭');
    };
    
    websocket.onerror = (error) => {
      console.error('顶部进度条WebSocket错误:', error);
    };
    
    return () => {
      if (websocket.readyState === WebSocket.OPEN) {
        websocket.close();
      }
    };
  }, [isVisible, searchId, onClose]);

  // 重置状态当组件隐藏时
  useEffect(() => {
    if (!isVisible) {
      setProgress(null);
      setIsComplete(false);
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
      setWs(null);
    }
  }, [isVisible, ws]);

  if (!isVisible || !progress) {
    return null;
  }

  const getProgressColor = () => {
    if (progress.status === 'completed') return 'bg-green-500';
    if (progress.status === 'failed') return 'bg-red-500';
    return 'bg-blue-500';
  };

  const getBackgroundColor = () => {
    if (progress.status === 'completed') return 'bg-green-50 border-green-200';
    if (progress.status === 'failed') return 'bg-red-50 border-red-200';
    return 'bg-blue-50 border-blue-200';
  };

  const getStatusIcon = () => {
    if (progress.status === 'completed') return <CheckCircle className="h-5 w-5 text-green-500" />;
    if (progress.status === 'failed') return <AlertCircle className="h-5 w-5 text-red-500" />;
    return <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />;
  };

  return (
    <div className={`fixed top-0 left-0 right-0 z-50 border-b shadow-sm ${getBackgroundColor()}`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between py-3">
          {/* 左侧：图标和标题 */}
          <div className="flex items-center space-x-3">
            <Mail className="h-5 w-5 text-blue-600" />
            <div className="flex items-center space-x-2">
              {getStatusIcon()}
              <span className="text-sm font-medium text-gray-900">
                {progress.title}
              </span>
            </div>
          </div>

          {/* 中间：进度信息 */}
          <div className="flex-1 mx-6">
            {/* 描述文字 */}
            <div className="text-sm text-gray-600 mb-1">
              {progress.description}
            </div>
            
            {/* 进度条 */}
            {progress.progress !== undefined && (
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className={`h-2 rounded-full transition-all duration-300 ${getProgressColor()}`}
                  style={{ width: `${progress.progress}%` }}
                ></div>
              </div>
            )}
            
            {/* 统计信息 */}
            {progress.total && (
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>总计: {progress.total}</span>
                <span>进度: {progress.progress || 0}%</span>
                <span>成功: {progress.sent || 0}</span>
                <span>失败: {progress.failed || 0}</span>
              </div>
            )}
          </div>

          {/* 右侧：关闭按钮 */}
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors p-1"
            title="关闭"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* 完成状态的详细信息 */}
        {isComplete && progress.result && (
          <div className="pb-3">
            <div className="bg-white rounded-lg p-3 shadow-sm">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  {progress.status === 'completed' ? (
                    <CheckCircle className="h-4 w-4 text-green-500" />
                  ) : (
                    <AlertCircle className="h-4 w-4 text-red-500" />
                  )}
                  <span className={`text-sm font-medium ${
                    progress.status === 'completed' ? 'text-green-800' : 'text-red-800'
                  }`}>
                    {progress.status === 'completed' ? '批量发送完成' : '批量发送失败'}
                  </span>
                </div>
                
                <div className="flex items-center space-x-4 text-xs text-gray-600">
                  <span>总计: {progress.result.total}</span>
                  <span className="text-green-600">成功: {progress.result.sent}</span>
                  <span className="text-red-600">失败: {progress.result.failed}</span>
                  {progress.result.sent > 0 && (
                    <span className="text-blue-600">
                      成功率: {Math.round((progress.result.sent / progress.result.total) * 100)}%
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default TopProgressBar;
