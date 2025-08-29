import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Mail, Send, Eye, User, FileText, Calendar, Quote, AlertCircle, CheckCircle, Loader2 } from 'lucide-react'
import { toast } from 'react-hot-toast'
import { searchAPI } from '../services/api'

interface EmailSenderProps {
  isOpen: boolean
  onClose: () => void
  authorEmail: string
  authorName: string
  paperTitle: string
  paperVenue?: string
  paperYear?: number
  paperCitations?: number
}

interface EmailPreview {
  success: boolean
  html_content: string
  template_data: any
}

const EmailSender: React.FC<EmailSenderProps> = ({
  isOpen,
  onClose,
  authorEmail,
  authorName,
  paperTitle,
  paperVenue,
  paperYear,
  paperCitations
}) => {
  const [subject, setSubject] = useState('')
  const [preview, setPreview] = useState<EmailPreview | null>(null)
  const [isLoadingPreview, setIsLoadingPreview] = useState(false)
  const [isSending, setIsSending] = useState(false)
  const [showPreview, setShowPreview] = useState(false)
  const [emailConfig, setEmailConfig] = useState<any>(null)

  // 初始化主题
  useEffect(() => {
    if (isOpen) {
      setSubject('Introducing ABKD: A Unified Framework for Knowledge Distillation (ICML 2025 Oral)')
    }
  }, [isOpen])

  // 检查邮件配置
  useEffect(() => {
    if (isOpen) {
      checkEmailConfig()
    }
  }, [isOpen])

  const checkEmailConfig = async () => {
    try {
      const config = await searchAPI.getEmailConfig()
      setEmailConfig(config)
      if (!config.valid) {
        toast.error(`邮件配置错误: ${config.message}`)
      }
    } catch (error) {
      toast.error('无法获取邮件配置')
      setEmailConfig({ valid: false, message: '配置检查失败' })
    }
  }

  const generatePreview = async () => {
    if (!authorName || !paperTitle) {
      toast.error('缺少必要信息')
      return
    }

    setIsLoadingPreview(true)
    try {
      const previewData = await searchAPI.previewEmail({
        author_name: authorName,
        paper_title: paperTitle,
        paper_venue: paperVenue,
        paper_year: paperYear,
        paper_citations: paperCitations
      })
      
      setPreview(previewData)
      setShowPreview(true)
      toast.success('邮件预览生成成功')
    } catch (error) {
      toast.error('生成邮件预览失败')
      console.error('Preview error:', error)
    } finally {
      setIsLoadingPreview(false)
    }
  }

  const sendEmail = async () => {
    if (!authorEmail || !subject || !authorName || !paperTitle) {
      toast.error('请填写完整信息')
      return
    }

    if (!emailConfig?.valid) {
      toast.error('邮件配置无效，无法发送邮件')
      return
    }

    setIsSending(true)
    try {
      const result = await searchAPI.sendEmail({
        to_email: authorEmail,
        subject: subject,
        author_name: authorName,
        paper_title: paperTitle,
        paper_venue: paperVenue,
        paper_year: paperYear,
        paper_citations: paperCitations
      })

      if (result.success) {
        toast.success(`邮件发送成功到 ${authorEmail}`)
        onClose()
      } else {
        toast.error(`邮件发送失败: ${result.message}`)
      }
    } catch (error) {
      toast.error('邮件发送失败')
      console.error('Send error:', error)
    } finally {
      setIsSending(false)
    }
  }

  if (!isOpen) return null

  return (
    <AnimatePresence>
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.95 }}
          className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-hidden"
        >
          {/* 头部 */}
          <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
            <div className="flex items-center space-x-3">
              <Mail className="h-6 w-6 text-blue-600 dark:text-blue-400" />
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                发送邮件
              </h2>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            >
              <X className="h-6 w-6" />
            </button>
          </div>

          <div className="flex h-[calc(90vh-80px)]">
            {/* 左侧：邮件信息 */}
            <div className="w-1/2 p-6 border-r border-gray-200 dark:border-gray-700 overflow-y-auto">
              {/* 邮件配置状态 */}
              {emailConfig && (
                <div className={`mb-4 p-3 rounded-lg flex items-center space-x-2 ${
                  emailConfig.valid 
                    ? 'bg-green-50 dark:bg-green-900/20 text-green-800 dark:text-green-200'
                    : 'bg-red-50 dark:bg-red-900/20 text-red-800 dark:text-red-200'
                }`}>
                  {emailConfig.valid ? (
                    <CheckCircle className="h-4 w-4" />
                  ) : (
                    <AlertCircle className="h-4 w-4" />
                  )}
                  <span className="text-sm">
                    {emailConfig.valid ? '邮件配置正常' : emailConfig.message}
                  </span>
                </div>
              )}

              {/* 收件人信息 */}
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    收件人
                  </label>
                  <div className="flex items-center space-x-2 p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
                    <User className="h-4 w-4 text-gray-500" />
                    <span className="text-sm text-gray-900 dark:text-white">{authorName}</span>
                    <span className="text-sm text-gray-500">({authorEmail})</span>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    邮件主题
                  </label>
                  <input
                    type="text"
                    value={subject}
                    onChange={(e) => setSubject(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    placeholder="输入邮件主题"
                  />
                </div>

                {/* 论文信息 */}
                <div className="space-y-3">
                  <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300">论文信息</h3>
                  
                  <div className="flex items-start space-x-2 p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
                    <FileText className="h-4 w-4 text-gray-500 mt-0.5" />
                    <div>
                      <div className="text-sm font-medium text-gray-900 dark:text-white">{paperTitle}</div>
                      {paperVenue && (
                        <div className="text-xs text-gray-500 mt-1">{paperVenue}</div>
                      )}
                    </div>
                  </div>

                  {paperYear && (
                    <div className="flex items-center space-x-2 text-sm text-gray-600 dark:text-gray-400">
                      <Calendar className="h-4 w-4" />
                      <span>{paperYear}</span>
                    </div>
                  )}

                  {paperCitations !== undefined && paperCitations > 0 && (
                    <div className="flex items-center space-x-2 text-sm text-gray-600 dark:text-gray-400">
                      <Quote className="h-4 w-4" />
                      <span>{paperCitations} 引用</span>
                    </div>
                  )}
                </div>

                {/* 操作按钮 */}
                <div className="space-y-3 pt-4">
                  <button
                    onClick={generatePreview}
                    disabled={isLoadingPreview || !authorName || !paperTitle}
                    className="w-full flex items-center justify-center space-x-2 px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isLoadingPreview ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Eye className="h-4 w-4" />
                    )}
                    <span>{isLoadingPreview ? '生成中...' : '预览邮件'}</span>
                  </button>

                  <button
                    onClick={sendEmail}
                    disabled={isSending || !authorEmail || !subject || !emailConfig?.valid}
                    className="w-full flex items-center justify-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isSending ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Send className="h-4 w-4" />
                    )}
                    <span>{isSending ? '发送中...' : '发送邮件'}</span>
                  </button>
                </div>
              </div>
            </div>

            {/* 右侧：邮件预览 */}
            <div className="w-1/2 p-6 overflow-y-auto">
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">邮件预览</h3>
              
              {showPreview && preview ? (
                <div className="border border-gray-200 dark:border-gray-600 rounded-lg overflow-hidden">
                  <iframe
                    srcDoc={preview.html_content}
                    className="w-full h-[600px] border-0"
                    title="邮件预览"
                  />
                </div>
              ) : (
                <div className="flex items-center justify-center h-[600px] border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg">
                  <div className="text-center">
                    <Eye className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                    <p className="text-gray-500 dark:text-gray-400">
                      点击"预览邮件"查看邮件内容
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  )
}

export default EmailSender
