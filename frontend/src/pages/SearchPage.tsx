import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation } from 'react-query'
import { motion } from 'framer-motion'
import { Search, Loader2, Calendar, SortDesc, FileText } from 'lucide-react'
import toast from 'react-hot-toast'
import { searchAPI, SearchRequest } from '../services/api'

const SearchPage = () => {
  const navigate = useNavigate()
  const currentYear = new Date().getFullYear()
  
  const [formData, setFormData] = useState<SearchRequest>({
    keyword: '',
    num_results: 50,
    sort_by: 'citations',
    start_year: undefined,
    end_year: undefined,
    filter_by_title: false,
    exclude_duplicates: false,
  })

  const searchMutation = useMutation(searchAPI.search, {
    onSuccess: (data) => {
      toast.success(`Found ${data.total_results} articles`)
      navigate(`/results/${data.search_id}`)
    },
    onError: () => {
      toast.error('Search failed. Please try again.')
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.keyword.trim()) {
      toast.error('Please enter a search keyword')
      return
    }
    searchMutation.mutate(formData)
  }

  return (
    <div className="max-w-4xl mx-auto">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center mb-12"
      >
        <h1 className="text-4xl md:text-5xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-purple-600 to-indigo-600 dark:from-purple-400 dark:to-indigo-400 mb-4">
          ScholarDock
        </h1>
        <p className="text-lg md:text-xl text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
          Discover, analyze, and visualize academic research with precision
        </p>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="relative"
      >
        <motion.form
          onSubmit={handleSubmit}
          className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg p-6 md:p-8 border border-gray-200 dark:border-gray-700"
        >
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Search Keywords
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Search className="h-5 w-5 text-purple-500" />
                </div>
                <input
                  type="text"
                  value={formData.keyword}
                  onChange={(e) => setFormData({ ...formData, keyword: e.target.value })}
                  placeholder="e.g., machine learning, artificial intelligence"
                  className="block w-full pl-10 pr-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                />
              </div>
            </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                <FileText className="inline h-4 w-4 mr-1 text-purple-500" />
                Number of Results
              </label>
              <input
                type="number"
                min="1"
                max="10000"
                value={formData.num_results}
                onChange={(e) => setFormData({ ...formData, num_results: parseInt(e.target.value) || 0 })}
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                placeholder="Enter number of results"
                list="num-results-options"
              />
              <datalist id="num-results-options">
                <option value="10" />
                <option value="20" />
                <option value="50" />
                <option value="100" />
                <option value="200" />
                <option value="500" />
                <option value="1000" />
              </datalist>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                <Calendar className="inline h-4 w-4 mr-1 text-purple-500" />
                Start Year
              </label>
              <input
                type="number"
                min="1900"
                max={currentYear}
                value={formData.start_year || ''}
                onChange={(e) => setFormData({ ...formData, start_year: e.target.value ? parseInt(e.target.value) : undefined })}
                placeholder="Optional"
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                <Calendar className="inline h-4 w-4 mr-1 text-purple-500" />
                End Year
              </label>
              <input
                type="number"
                min="1900"
                max={currentYear}
                value={formData.end_year || ''}
                onChange={(e) => setFormData({ ...formData, end_year: e.target.value ? parseInt(e.target.value) : undefined })}
                placeholder="Optional"
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              <SortDesc className="inline h-4 w-4 mr-1 text-purple-500" />
              Sort By
            </label>
            <div className="relative">
              <select
                value={formData.sort_by}
                onChange={(e) => setFormData({ ...formData, sort_by: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white appearance-none"
              >
                <option value="citations">Total Citations</option>
                <option value="citations_per_year">Citations per Year</option>
                <option value="year">Publication Year</option>
              </select>
              <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-gray-700 dark:text-gray-300">
                <svg className="fill-current h-4 w-4" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">
                  <path d="M9.293 12.95l.707.707L15.657 8l-1.414-1.414L10 10.828 5.757 6.586 4.343 8z" />
                </svg>
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between">
            <span className="flex-grow flex flex-col">
              <span className="text-sm font-medium text-gray-900 dark:text-gray-100">Filter by Title</span>
              <span className="text-xs text-gray-500 dark:text-gray-400">
                Only include papers with keywords in the title
              </span>
            </span>
            <label htmlFor="filter-by-title-toggle" className="inline-flex relative items-center cursor-pointer">
              <input
                type="checkbox"
                id="filter-by-title-toggle"
                className="sr-only peer"
                checked={formData.filter_by_title}
                onChange={(e) => setFormData({ ...formData, filter_by_title: e.target.checked })}
              />
              <div className="w-11 h-6 bg-gray-300 rounded-full peer peer-focus:ring-2 peer-focus:ring-purple-300 dark:peer-focus:ring-purple-800 dark:bg-gray-600 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-purple-600"></div>
            </label>
          </div>

          <div className="flex items-center justify-between">
            <span className="flex-grow flex flex-col">
              <span className="text-sm font-medium text-gray-900 dark:text-gray-100">Exclude Duplicates</span>
              <span className="text-xs text-gray-500 dark:text-gray-400">
                Filter out papers that have appeared in previous searches
              </span>
            </span>
            <label htmlFor="exclude-duplicates-toggle" className="inline-flex relative items-center cursor-pointer">
              <input
                type="checkbox"
                id="exclude-duplicates-toggle"
                className="sr-only peer"
                checked={formData.exclude_duplicates}
                onChange={(e) => setFormData({ ...formData, exclude_duplicates: e.target.checked })}
              />
              <div className="w-11 h-6 bg-gray-300 rounded-full peer peer-focus:ring-2 peer-focus:ring-purple-300 dark:peer-focus:ring-purple-800 dark:bg-gray-600 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-purple-600"></div>
            </label>
          </div>

          <button
            type="submit"
            disabled={searchMutation.isLoading}
            className="w-full py-3 px-4 bg-purple-600 hover:bg-purple-700 text-white font-medium rounded-lg transition-colors duration-200 flex items-center justify-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {searchMutation.isLoading ? (
              <>
                <Loader2 className="h-5 w-5 animate-spin" />
                <span>Searching...</span>
              </>
            ) : (
              <>
                <Search className="h-5 w-5" />
                <span>Search Google Scholar</span>
              </>
            )}
          </button>
        </div>
      </motion.form>
    </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="mt-8 bg-gray-50 dark:bg-gray-800 rounded-xl p-6"
      >
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-3 text-center">
          💬 Join Our Community
        </h3>
        <p className="text-sm text-gray-600 dark:text-gray-400 text-center mb-4">
          Get help, share feedback, and connect with other users
        </p>
        <div className="flex flex-wrap justify-center gap-3">
          <a
            href="https://discord.gg/nCnmRBM4"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center space-x-2 px-3 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm transition-colors"
          >
            <span>🎮</span>
            <span>Discord</span>
          </a>
          <a
            href="https://t.me/ScholarDock"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center space-x-2 px-3 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg text-sm transition-colors"
          >
            <span>✈️</span>
            <span>Telegram</span>
          </a>
          <span className="inline-flex items-center space-x-2 px-3 py-2 bg-purple-600 text-white rounded-lg text-sm">
            <span>📱</span>
            <span>WeChat: 15279836691</span>
          </span>
        </div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
        className="mt-8 text-center text-sm text-gray-600 dark:text-gray-400"
      >
        <p>This tool is for educational purposes only.</p>
        <p>Please respect Google Scholar's terms of service.</p>
      </motion.div>
    </div>
  )
}

export default SearchPage