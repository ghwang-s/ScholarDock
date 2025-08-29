import { useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from 'react-query'
import { useState } from 'react'
import { motion } from 'framer-motion'
import { ExternalLink, Users, Calendar, Quote, Trophy, TrendingUp, Filter, Mail, Download, Wifi, WifiOff, Send, MailPlus } from 'lucide-react'
import { searchAPI, AuthorEmail } from '../services/api'
import CitationChart from '../components/CitationChart'
import EmailSender from '../components/EmailSender'
import BatchEmailSender from '../components/BatchEmailSender'
import TopProgressBar from '../components/TopProgressBar'
// import PDFExtractionProgress from '../components/PDFExtractionProgress' // 已禁用
import { toast } from 'react-hot-toast'

const ResultsPage = () => {
  const { searchId } = useParams<{ searchId: string }>()
  const [filterYear, setFilterYear] = useState<number | null>(null)
  const [filterMinCitations, setFilterMinCitations] = useState<number>(0)
  const [extractingEmails, setExtractingEmails] = useState<Set<number>>(new Set())
  // 邮件发送相关状态
  const [showEmailSender, setShowEmailSender] = useState(false)
  const [selectedEmailData, setSelectedEmailData] = useState<{
    authorEmail: string
    authorName: string
    paperTitle: string
    paperVenue?: string
    paperYear?: number
    paperCitations?: number
  } | null>(null)
  // 批量邮件发送相关状态
  const [showBatchEmailSender, setShowBatchEmailSender] = useState(false)
  const [showTopProgressBar, setShowTopProgressBar] = useState(false)
  // PDF进度相关状态已禁用
  // const [showPDFProgress, setShowPDFProgress] = useState<boolean>(false)
  // const [currentArticleId, setCurrentArticleId] = useState<number | null>(null)
  // const [progressData, setProgressData] = useState<any>(null)
  // const websocketRef = useRef<WebSocket | null>(null)
  const queryClient = useQueryClient()

  // 代理状态查询
  const { data: proxyStatus } = useQuery(
    'proxyStatus',
    () => searchAPI.getProxyStatus(),
    {
      refetchInterval: 30000, // 每30秒检查一次
      retry: false
    }
  )

  const { data: search, isLoading } = useQuery(
    ['searchDetails', searchId],
    () => searchAPI.getSearchDetails(parseInt(searchId!)),
    { enabled: !!searchId }
  )

  // 提取单篇论文作者邮箱的mutation
  const extractEmailsMutation = useMutation(
    (articleId: number) => searchAPI.extractAuthorEmails(articleId),
    {
      onMutate: (articleId) => {
        setExtractingEmails(prev => new Set(prev).add(articleId))
        // 禁用PDF提取进度组件显示
        // setCurrentArticleId(articleId);
        // setShowPDFProgress(true);
        // setProgressData(null);
      },
      onSuccess: (data, articleId) => {
        const authorEmailsCount = data.author_emails?.filter(e => e.email_source !== 'pdf_fallback' && e.email).length || 0;
        const pdfEmailsCount = data.author_emails?.filter(e => e.email_source === 'pdf_fallback').length || 0;
        toast.success(`提取完成！作者邮箱 ${authorEmailsCount} 个，PDF邮箱 ${pdfEmailsCount} 个。`);

        // 通过使查询失效来强制重新获取数据，确保UI更新
        queryClient.invalidateQueries(['searchDetails', searchId]);
      },
      onError: (error: any, articleId) => {
        toast.error(`提取邮箱失败: ${error.response?.data?.detail || error.message}`)
      },
      onSettled: (data, error, articleId) => {
        setExtractingEmails(prev => {
          const newSet = new Set(prev)
          newSet.delete(articleId)
          return newSet
        })
      }
    }
  )

  // 提取所有论文作者邮箱的mutation
  const extractAllEmailsMutation = useMutation(
    () => searchAPI.extractAllAuthorEmails(parseInt(searchId!)),
    {
      onSuccess: (data) => {
        toast.success(`已开始提取 ${data.total_articles} 篇论文的作者邮箱，请稍后刷新查看结果`)
      },
      onError: (error: any) => {
        toast.error(`批量提取邮箱失败: ${error.response?.data?.detail || error.message}`)
      }
    }
  )

  // 建立WebSocket连接 - 已禁用
  // useEffect(() => {
  //   // WebSocket连接代码已禁用，不再显示PDF提取进度窗口
  // }, [searchId]);

  // 处理发邮件
  const handleSendEmail = (authorEmail: string, authorName: string, article: any) => {
    setSelectedEmailData({
      authorEmail,
      authorName,
      paperTitle: article.title,
      paperVenue: article.venue,
      paperYear: article.year,
      paperCitations: article.citations
    })
    setShowEmailSender(true)
  }

  const handleCloseEmailSender = () => {
    setShowEmailSender(false)
    setSelectedEmailData(null)
  }

  if (isLoading || !search) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  const filteredArticles = search.articles?.filter(article => {
    if (filterYear && article.year !== filterYear) return false
    if (article.citations < filterMinCitations) return false
    return true
  }) || []

  const yearOptions = [...new Set(search.articles?.map(a => a.year).filter(Boolean))].sort((a, b) => b! - a!)

  return (
    <div>
      <div className="mb-8">
        {/* 代理状态显示 */}
        {proxyStatus && (
          <div className={`mb-4 p-3 rounded-lg border ${
            proxyStatus.status === 'connected'
              ? 'bg-green-50 border-green-200 text-green-800'
              : proxyStatus.status === 'disabled'
              ? 'bg-gray-50 border-gray-200 text-gray-600'
              : 'bg-red-50 border-red-200 text-red-800'
          }`}>
            <div className="flex items-center">
              {proxyStatus.status === 'connected' ? (
                <Wifi className="h-4 w-4 mr-2" />
              ) : (
                <WifiOff className="h-4 w-4 mr-2" />
              )}
              <span className="text-sm font-medium">
                代理状态: {proxyStatus.status === 'connected' ? '已连接' :
                         proxyStatus.status === 'disabled' ? '未启用' : '连接失败'}
              </span>
              {proxyStatus.proxy_url && (
                <span className="ml-2 text-xs opacity-75">({proxyStatus.proxy_url})</span>
              )}
              {proxyStatus.message && (
                <span className="ml-2 text-xs">- {proxyStatus.message}</span>
              )}
            </div>
          </div>
        )}

        <div className="flex justify-between items-start mb-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
              Results for "{search.keyword}"
            </h1>
            <p className="text-gray-600 dark:text-gray-400">
              Found {search.total_results} articles
            </p>
          </div>
          <div className="flex space-x-2">
            <button
              onClick={() => extractAllEmailsMutation.mutate()}
              disabled={extractAllEmailsMutation.isLoading || proxyStatus?.status !== 'connected'}
              className="flex items-center px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              title={proxyStatus?.status !== 'connected' ? '需要代理连接才能提取邮箱' : ''}
            >
              <Download className="h-4 w-4 mr-2" />
              {extractAllEmailsMutation.isLoading ? '提取中...' : '批量提取作者邮箱'}
            </button>
            <button
              onClick={() => setShowBatchEmailSender(true)}
              className="flex items-center px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
              title="批量发送邮件给所有提取到的邮箱"
            >
              <MailPlus className="h-4 w-4 mr-2" />
              批量发送邮件
            </button>
          </div>
        </div>
      </div>

      {search.articles && search.articles.length > 0 && (
        <div className="mb-8">
          <CitationChart articles={search.articles} />
        </div>
      )}

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-4 mb-6">
        <div className="flex items-center space-x-4">
          <Filter className="h-5 w-5 text-gray-600 dark:text-gray-400" />
          
          <select
            value={filterYear || ''}
            onChange={(e) => setFilterYear(e.target.value ? parseInt(e.target.value) : null)}
            className="px-3 py-1 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-sm"
          >
            <option value="">All Years</option>
            {yearOptions.map(year => (
              <option key={year} value={year}>{year}</option>
            ))}
          </select>
          
          <div className="flex items-center space-x-2">
            <label className="text-sm text-gray-600 dark:text-gray-400">
              Min Citations:
            </label>
            <input
              type="number"
              min="0"
              value={filterMinCitations}
              onChange={(e) => setFilterMinCitations(parseInt(e.target.value) || 0)}
              className="w-20 px-2 py-1 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-sm"
            />
          </div>
          
          <span className="text-sm text-gray-600 dark:text-gray-400 ml-auto">
            Showing {filteredArticles.length} of {search.articles?.length || 0} articles
          </span>
        </div>
      </div>

      <div className="space-y-4">
        {filteredArticles.map((article, index) => (
          <motion.article
            key={index}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.05 }}
            className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow"
          >
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
              {article.url ? (
                <a
                  href={article.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-primary-600 transition-colors flex items-center"
                >
                  {article.title}
                  <ExternalLink className="h-4 w-4 ml-2" />
                </a>
              ) : (
                article.title
              )}
            </h3>

            <div className="flex flex-wrap gap-4 text-sm text-gray-600 dark:text-gray-400 mb-3">
              {article.authors && (
                <span className="flex items-center">
                  <Users className="h-4 w-4 mr-1" />
                  {article.authors}
                </span>
              )}

              {article.year && (
                <span className="flex items-center">
                  <Calendar className="h-4 w-4 mr-1" />
                  {article.year}
                </span>
              )}

              {article.venue && (
                <span>{article.venue}</span>
              )}

              {article.publisher && (
                <span>{article.publisher}</span>
              )}
            </div>

            {/* 作者邮箱信息 */}
            {article.author_links && article.author_links.length > 0 && (
              <div className="mb-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    作者信息 (前3位):
                  </span>
                  {!article.author_emails && (
                    <button
                      onClick={() => extractEmailsMutation.mutate(article.id!)}
                      disabled={
                        extractingEmails.has(article.id!) ||
                        extractEmailsMutation.isLoading ||
                        proxyStatus?.status !== 'connected'
                      }
                      className="flex items-center px-3 py-1 text-xs bg-blue-100 text-blue-700 rounded-md hover:bg-blue-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      title={proxyStatus?.status !== 'connected' ? '需要代理连接才能提取邮箱' : ''}
                    >
                      <Mail className="h-3 w-3 mr-1" />
                      {extractingEmails.has(article.id!) ? '提取中...' : '提取邮箱'}
                    </button>
                  )}
                </div>

                <div className="space-y-1">
                  {article.author_links.map((author, idx) => {
                    const authorEmail = article.author_emails?.find(email => email.name === author.name);
                    return (
                      <div key={idx} className="flex items-center justify-between text-xs bg-gray-50 dark:bg-gray-700 rounded p-2">
                        <div className="flex items-center space-x-2">
                          <span className="font-medium">{author.name}</span>
                          <a
                            href={author.scholar_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-600 hover:text-blue-800 transition-colors"
                            title="Google Scholar主页"
                          >
                            <ExternalLink className="h-3 w-3" />
                          </a>
                        </div>
                        <div className="flex items-center space-x-1">
                          {authorEmail ? (
                            authorEmail.email && authorEmail.email_source !== 'pdf_fallback' ? (
                              <>
                                <Mail className="h-3 w-3 text-green-600" />
                                <span className="text-green-600 font-mono">{authorEmail.email}</span>
                                <span className="text-gray-500">({authorEmail.email_source})</span>
                                <button
                                  onClick={() => handleSendEmail(authorEmail.email!, author.name, article)}
                                  className="ml-2 p-1 text-blue-600 hover:text-blue-800 hover:bg-blue-50 rounded transition-colors"
                                  title="发送邮件"
                                >
                                  <Send className="h-3 w-3" />
                                </button>
                              </>
                            ) : authorEmail.email_source === 'pdf_fallback' ? (
                              <>
                                <Mail className="h-3 w-3 text-indigo-600" />
                                <span className="text-indigo-600 font-mono">PDF提取</span>
                              </>
                            ) : (
                              <>
                                <Mail className="h-3 w-3 text-gray-400" />
                                <span className="text-gray-500 font-mono">None</span>
                                <span className="text-gray-400">({authorEmail.email_source})</span>
                              </>
                            )
                          ) : (
                            article.author_emails ? (
                              <>
                                <Mail className="h-3 w-3 text-gray-400" />
                                <span className="text-gray-500 font-mono">None</span>
                                <span className="text-gray-400">(not_extracted)</span>
                              </>
                            ) : null
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* PDF提取的邮箱 - 新逻辑 */}
                {(() => {
                  const pdfFallbackEmails = article.author_emails?.filter(email => email.email_source === 'pdf_fallback') || [];
                  // 对PDF邮箱进行去重
                  const uniquePdfFallbackEmails = Array.from(new Set(pdfFallbackEmails.map(email => email.email)))
                    .map(email => pdfFallbackEmails.find(e => e.email === email))
                    .filter(Boolean) as typeof pdfFallbackEmails;
                  
                  if (uniquePdfFallbackEmails.length === 0) return null;

                  return (
                    <div className="mt-3 p-3 bg-indigo-50 dark:bg-indigo-900/20 rounded-lg border border-indigo-200 dark:border-indigo-800">
                      <div className="flex items-center mb-2">
                        <Mail className="h-4 w-4 text-indigo-600 dark:text-indigo-400 mr-2" />
                        <span className="text-sm font-medium text-indigo-800 dark:text-indigo-200">
                          通过PDF提取的邮箱 ({uniquePdfFallbackEmails.length} 个):
                        </span>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {uniquePdfFallbackEmails.map((authorEmail, idx) => (
                          <div
                            key={`pdf-${idx}`}
                            className="inline-flex items-center px-2 py-1 bg-indigo-100 dark:bg-indigo-800 text-indigo-800 dark:text-indigo-200 text-xs font-mono rounded-md"
                          >
                            <span>{authorEmail.email}</span>
                            <button
                              onClick={() => handleSendEmail(authorEmail.email!, `authors of paper ${article.title}`, article)}
                              className="ml-2 p-0.5 text-indigo-600 hover:text-indigo-800 hover:bg-indigo-200 rounded transition-colors"
                              title="发送邮件"
                            >
                              <Send className="h-3 w-3" />
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })()}
              </div>
            )}

            {article.description && (
              <p className="text-gray-700 dark:text-gray-300 mb-3 line-clamp-3">
                <Quote className="inline h-4 w-4 mr-1" />
                {article.description}
              </p>
            )}

            <div className="flex items-center space-x-4 text-sm">
              <span className="flex items-center text-primary-600 dark:text-primary-400 font-medium">
                <Trophy className="h-4 w-4 mr-1" />
                {article.citations} citations
              </span>
              
              {article.citations_per_year > 0 && (
                <span className="flex items-center text-green-600 dark:text-green-400 font-medium">
                  <TrendingUp className="h-4 w-4 mr-1" />
                  {article.citations_per_year.toFixed(1)}/year
                </span>
              )}
            </div>
          </motion.article>
        ))}
      </div>

      {/* PDF提取进度组件已禁用 */}
      {/* <PDFExtractionProgress
        articleId={currentArticleId || 0}
        isOpen={showPDFProgress}
        onClose={() => setShowPDFProgress(false)}
      /> */}

      {/* 邮件发送组件 */}
      {selectedEmailData && (
        <EmailSender
          isOpen={showEmailSender}
          onClose={handleCloseEmailSender}
          authorEmail={selectedEmailData.authorEmail}
          authorName={selectedEmailData.authorName}
          paperTitle={selectedEmailData.paperTitle}
          paperVenue={selectedEmailData.paperVenue}
          paperYear={selectedEmailData.paperYear}
          paperCitations={selectedEmailData.paperCitations}
        />
      )}

      {/* 批量发送邮件组件 */}
      {showBatchEmailSender && searchId && (
        <BatchEmailSender
          searchId={parseInt(searchId)}
          totalArticles={search.articles?.length || 0}
          onClose={() => {
            setShowBatchEmailSender(false)
            setShowTopProgressBar(true)
          }}
        />
      )}

      {/* 顶部进度条 */}
      <TopProgressBar
        searchId={searchId ? parseInt(searchId) : undefined}
        isVisible={showTopProgressBar}
        onClose={() => setShowTopProgressBar(false)}
      />
    </div>
  )
}

export default ResultsPage