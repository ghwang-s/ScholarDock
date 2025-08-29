import React, { useState, useEffect } from 'react';
import { Mail, Send, X, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';

interface BatchEmailSenderProps {
  searchId: number;
  totalArticles: number;
  onClose: () => void;
}

interface BatchProgress {
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

const BatchEmailSender: React.FC<BatchEmailSenderProps> = ({
  searchId,
  totalArticles,
  onClose
}) => {
  const [subject, setSubject] = useState('Introducing ABKD: A Unified Framework for Knowledge Distillation (ICML 2025 Oral)');
  const [includeAuthorEmails, setIncludeAuthorEmails] = useState(true);
  const [includePdfEmails, setIncludePdfEmails] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [progress, setProgress] = useState<BatchProgress | null>(null);
  const [isComplete, setIsComplete] = useState(false);
  const [ws, setWs] = useState<WebSocket | null>(null);

  // WebSocket连接
  useEffect(() => {
    const websocket = new WebSocket(`ws://127.0.0.1:8002/ws/batch_email_${searchId}`);
    
    websocket.onopen = () => {
      console.log('批量邮件WebSocket连接已建立');
      setWs(websocket);
    };
    
    websocket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log('收到批量邮件进度更新:', data);
        setProgress(data);
        
        if (data.type === 'completion') {
          setIsLoading(false);
          setIsComplete(true);
        }
      } catch (error) {
        console.error('解析WebSocket消息失败:', error);
      }
    };
    
    websocket.onclose = () => {
      console.log('批量邮件WebSocket连接已关闭');
    };
    
    websocket.onerror = (error) => {
      console.error('批量邮件WebSocket错误:', error);
    };
    
    return () => {
      if (websocket.readyState === WebSocket.OPEN) {
        websocket.close();
      }
    };
  }, [searchId]);

  const handleBatchSend = async () => {
    if (!subject.trim()) {
      alert('请输入邮件主题');
      return;
    }

    if (!includeAuthorEmails && !includePdfEmails) {
      alert('请至少选择一种邮箱类型');
      return;
    }

    setIsLoading(true);
    setProgress(null);
    setIsComplete(false);

    try {
      const response = await fetch('http://127.0.0.1:8002/api/email/batch-send', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          search_id: searchId,
          subject: subject,
          include_author_emails: includeAuthorEmails,
          include_pdf_emails: includePdfEmails
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '批量发送失败');
      }

      const result = await response.json();
      console.log('批量发送启动成功:', result);
      
    } catch (error) {
      console.error('批量发送失败:', error);
      alert(`批量发送失败: ${error instanceof Error ? error.message : '未知错误'}`);
      setIsLoading(false);
    }
  };

  const getProgressColor = () => {
    if (progress?.status === 'completed') return 'bg-green-500';
    if (progress?.status === 'failed') return 'bg-red-500';
    return 'bg-blue-500';
  };

  const getStatusIcon = () => {
    if (progress?.status === 'completed') return <CheckCircle className="h-5 w-5 text-green-500" />;
    if (progress?.status === 'failed') return <AlertCircle className="h-5 w-5 text-red-500" />;
    if (isLoading) return <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />;
    return <Mail className="h-5 w-5 text-gray-500" />;
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
        {/* 头部 */}
        <div className="flex items-center justify-between p-6 border-b">
          <div className="flex items-center space-x-2">
            <Mail className="h-6 w-6 text-blue-600" />
            <h2 className="text-xl font-semibold text-gray-900">批量发送邮件</h2>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
            disabled={isLoading}
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        {/* 内容 */}
        <div className="p-6 space-y-4">
          {/* 搜索信息 */}
          <div className="bg-gray-50 rounded-lg p-4">
            <p className="text-sm text-gray-600">
              搜索ID: <span className="font-medium">{searchId}</span>
            </p>
            <p className="text-sm text-gray-600">
              文章数量: <span className="font-medium">{totalArticles}</span>
            </p>
          </div>

          {/* 邮件主题 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              邮件主题
            </label>
            <input
              type="text"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="请输入邮件主题"
              disabled={isLoading}
            />
          </div>

          {/* 邮箱类型选择 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              发送范围
            </label>
            <div className="space-y-2">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={includeAuthorEmails}
                  onChange={(e) => setIncludeAuthorEmails(e.target.checked)}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  disabled={isLoading}
                />
                <span className="ml-2 text-sm text-gray-700">作者邮箱（个人主页提取）</span>
              </label>
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={includePdfEmails}
                  onChange={(e) => setIncludePdfEmails(e.target.checked)}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  disabled={isLoading}
                />
                <span className="ml-2 text-sm text-gray-700">PDF邮箱（论文中提取）</span>
              </label>
            </div>
          </div>

          {/* 进度显示 */}
          {(isLoading || progress) && (
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="flex items-center space-x-2 mb-2">
                {getStatusIcon()}
                <span className="text-sm font-medium text-gray-900">
                  {progress?.title || '准备发送...'}
                </span>
              </div>
              
              {progress?.description && (
                <p className="text-sm text-gray-600 mb-2">{progress.description}</p>
              )}
              
              {progress?.progress !== undefined && (
                <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
                  <div
                    className={`h-2 rounded-full transition-all duration-300 ${getProgressColor()}`}
                    style={{ width: `${progress.progress}%` }}
                  ></div>
                </div>
              )}
              
              {progress?.total && (
                <div className="flex justify-between text-xs text-gray-500">
                  <span>总计: {progress.total}</span>
                  <span>成功: {progress.sent || 0}</span>
                  <span>失败: {progress.failed || 0}</span>
                </div>
              )}
            </div>
          )}

          {/* 完成结果 */}
          {isComplete && progress?.result && (
            <div className={`rounded-lg p-4 ${
              progress.status === 'completed' ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'
            }`}>
              <div className="flex items-center space-x-2 mb-2">
                {progress.status === 'completed' ? (
                  <CheckCircle className="h-5 w-5 text-green-500" />
                ) : (
                  <AlertCircle className="h-5 w-5 text-red-500" />
                )}
                <span className={`text-sm font-medium ${
                  progress.status === 'completed' ? 'text-green-800' : 'text-red-800'
                }`}>
                  {progress.status === 'completed' ? '发送完成' : '发送失败'}
                </span>
              </div>
              <div className="text-sm text-gray-600">
                <p>总计: {progress.result.total} 封邮件</p>
                <p>成功: {progress.result.sent} 封</p>
                <p>失败: {progress.result.failed} 封</p>
                {progress.result.sent > 0 && (
                  <p className="text-green-600 mt-1">
                    成功率: {Math.round((progress.result.sent / progress.result.total) * 100)}%
                  </p>
                )}
              </div>
            </div>
          )}
        </div>

        {/* 底部按钮 */}
        <div className="flex justify-end space-x-3 p-6 border-t bg-gray-50">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
            disabled={isLoading}
          >
            {isComplete ? '关闭' : '取消'}
          </button>
          {!isComplete && (
            <button
              onClick={handleBatchSend}
              disabled={isLoading || !subject.trim() || (!includeAuthorEmails && !includePdfEmails)}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center space-x-2"
            >
              {isLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
              <span>{isLoading ? '发送中...' : '开始发送'}</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default BatchEmailSender;
