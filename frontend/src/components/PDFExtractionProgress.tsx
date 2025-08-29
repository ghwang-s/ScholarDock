import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Loader2, CheckCircle, XCircle, FileText, Users, Download, AlertCircle } from 'lucide-react'

interface PDFExtractionStep {
  id: string
  title: string
  status: 'pending' | 'in_progress' | 'completed' | 'failed'
  description?: string
}

interface PDFExtractionProgressProps {
  articleId: number
  isOpen: boolean
  onClose: () => void
}

const PDFExtractionProgress = ({ articleId, isOpen, onClose }: PDFExtractionProgressProps) => {
  const [steps, setSteps] = useState<PDFExtractionStep[]>([
    {
      id: 'start',
      title: '开始PDF邮箱提取',
      status: 'pending',
      description: '初始化PDF邮箱提取过程'
    },
    {
      id: 'get_pdf_links',
      title: '获取PDF链接',
      status: 'pending',
      description: '从Google Scholar获取论文PDF链接'
    },
    {
      id: 'download_pdf',
      title: '下载PDF文件',
      status: 'pending',
      description: '下载论文PDF文件'
    },
    {
      id: 'extract_text',
      title: '提取PDF文本',
      status: 'pending',
      description: '从PDF第一页提取文本内容'
    },
    {
      id: 'find_emails',
      title: '查找邮箱地址',
      status: 'pending',
      description: '在PDF文本中查找作者邮箱'
    },
    {
      id: 'match_authors',
      title: '匹配作者邮箱',
      status: 'pending',
      description: '将找到的邮箱与作者姓名匹配'
    },
    {
      id: 'complete',
      title: '完成提取',
      status: 'pending',
      description: '保存提取结果'
    }
  ])

  const [currentStep, setCurrentStep] = useState(0)
  const [isExtracting, setIsExtracting] = useState(true)
  const [extractionResult, setExtractionResult] = useState<{ success: boolean; message: string } | null>(null)

  // 模拟进度更新
  useEffect(() => {
    if (!isOpen) return

    const simulateProgress = async () => {
      // 模拟实际的提取过程
      for (let i = 0; i < steps.length; i++) {
        // 更新当前步骤状态
        setSteps(prev => prev.map((step, idx) => 
          idx < i ? {...step, status: 'completed'} :
          idx === i ? {...step, status: 'in_progress'} :
          step
        ))
        
        setCurrentStep(i)
        
        // 模拟步骤执行时间
        await new Promise(resolve => setTimeout(resolve, 2000 + Math.random() * 3000))
      }
      
      // 完成所有步骤
      setSteps(prev => prev.map(step => ({...step, status: 'completed'})))
      setIsExtracting(false)
      setExtractionResult({
        success: true,
        message: '成功提取2个作者邮箱'
      })
    }

    simulateProgress()
  }, [isOpen, steps.length])

  const getStepIcon = (step: PDFExtractionStep) => {
    switch (step.status) {
      case 'completed':
        return <CheckCircle className="h-5 w-5 text-green-500" />
      case 'in_progress':
        return <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />
      case 'failed':
        return <XCircle className="h-5 w-5 text-red-500" />
      default:
        return <div className="h-5 w-5 rounded-full border-2 border-gray-300" />
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-hidden flex flex-col"
      >
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold text-gray-900 dark:text-white flex items-center">
              <FileText className="h-6 w-6 mr-2 text-blue-500" />
              PDF邮箱提取进度
            </h2>
            <button
              onClick={onClose}
              className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
            >
              <XCircle className="h-6 w-6" />
            </button>
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            论文ID: {articleId}
          </p>
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          <div className="space-y-4">
            {steps.map((step, index) => (
              <motion.div
                key={step.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 }}
                className={`flex items-start p-4 rounded-lg border ${
                  step.status === 'in_progress'
                    ? 'bg-blue-50 border-blue-200 dark:bg-blue-900/20 dark:border-blue-800'
                    : step.status === 'completed'
                    ? 'bg-green-50 border-green-200 dark:bg-green-900/20 dark:border-green-800'
                    : step.status === 'failed'
                    ? 'bg-red-50 border-red-200 dark:bg-red-900/20 dark:border-red-800'
                    : 'bg-gray-50 border-gray-200 dark:bg-gray-700/50 dark:border-gray-600'
                }`}
              >
                <div className="mr-3 mt-0.5">
                  {getStepIcon(step)}
                </div>
                <div className="flex-1">
                  <h3 className={`font-medium ${
                    step.status === 'in_progress'
                      ? 'text-blue-700 dark:text-blue-300'
                      : step.status === 'completed'
                      ? 'text-green-700 dark:text-green-300'
                      : step.status === 'failed'
                      ? 'text-red-700 dark:text-red-300'
                      : 'text-gray-700 dark:text-gray-300'
                  }`}>
                    {step.title}
                  </h3>
                  {step.description && (
                    <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                      {step.description}
                    </p>
                  )}
                  {step.status === 'in_progress' && (
                    <div className="mt-2 flex items-center text-sm text-blue-600 dark:text-blue-400">
                      <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                      正在执行...
                    </div>
                  )}
                </div>
              </motion.div>
            ))}
          </div>

          {extractionResult && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className={`mt-6 p-4 rounded-lg border ${
                extractionResult.success
                  ? 'bg-green-50 border-green-200 dark:bg-green-900/20 dark:border-green-800'
                  : 'bg-red-50 border-red-200 dark:bg-red-900/20 dark:border-red-800'
              }`}
            >
              <div className="flex items-center">
                {extractionResult.success ? (
                  <CheckCircle className="h-5 w-5 text-green-500 mr-2" />
                ) : (
                  <AlertCircle className="h-5 w-5 text-red-500 mr-2" />
                )}
                <span className={`font-medium ${
                  extractionResult.success
                    ? 'text-green-700 dark:text-green-300'
                    : 'text-red-700 dark:text-red-300'
                }`}>
                  {extractionResult.message}
                </span>
              </div>
            </motion.div>
          )}
        </div>

        <div className="p-6 border-t border-gray-200 dark:border-gray-700 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300 dark:bg-gray-700 dark:text-white dark:hover:bg-gray-600 transition-colors"
          >
            关闭
          </button>
        </div>
      </motion.div>
    </div>
  )
}

export default PDFExtractionProgress