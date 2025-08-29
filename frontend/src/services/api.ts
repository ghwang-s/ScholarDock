import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

export interface SearchRequest {
  keyword: string
  num_results: number
  start_year?: number
  end_year?: number
  sort_by: string
  filter_by_title?: boolean
  exclude_duplicates?: boolean
}

export interface AuthorLink {
  name: string
  scholar_url: string
}

export interface AuthorEmail {
  name: string
  email: string | null
  email_source: string
  homepage?: string
}

export interface Article {
  id?: number
  title: string
  authors?: string
  author_links?: AuthorLink[]
  author_emails?: AuthorEmail[]
  pdf_fallback_emails?: string[]
  venue?: string
  publisher?: string
  year?: number
  citations: number
  citations_per_year: number
  description?: string
  url?: string
  created_at?: string
}

export interface SearchResponse {
  search_id: number
  keyword: string
  total_results: number
  articles: Article[]
  message: string
}

export interface Search {
  id: number
  keyword: string
  start_year?: number
  end_year?: number
  total_results: number
  created_at: string
  articles?: Article[]
}


export const searchAPI = {
  search: async (params: SearchRequest): Promise<SearchResponse> => {
    const { data } = await api.post<SearchResponse>('/search', params)
    return data
  },

  getSearchHistory: async (skip = 0, limit = 20): Promise<Search[]> => {
    const { data } = await api.get<Search[]>('/searches', { params: { skip, limit } })
    return data
  },

  getSearchDetails: async (searchId: number): Promise<Search> => {
    const { data } = await api.get<Search>(`/search/${searchId}`)
    return data
  },

  deleteSearch: async (searchId: number): Promise<void> => {
    await api.delete(`/search/${searchId}`)
  },

  extractAuthorEmails: async (articleId: number): Promise<{
    message: string;
    author_emails: AuthorEmail[];
    pdf_fallback_emails: string[];
  }> => {
    const { data } = await api.post(`/extract-author-emails/${articleId}`);
    return data;
  },

  extractAllAuthorEmails: async (searchId: number): Promise<{ message: string; search_id: number; total_articles: number }> => {
    const { data } = await api.post(`/extract-all-author-emails/${searchId}`)
    return data
  },

  getProxyStatus: async (): Promise<{ proxy_enabled: boolean; proxy_url: string | null; status: string; message?: string }> => {
    const { data } = await api.get('/proxy-status')
    return data
  },

  exportResults: async (searchId: number, format: string): Promise<Blob> => {
    const { data } = await api.get(`/export/${searchId}`, {
      params: { format },
      responseType: 'blob',
    })
    return data
  },

  // 邮件相关API
  previewEmail: async (data: {
    author_name: string
    paper_title: string
    paper_venue?: string
    paper_year?: number
    paper_citations?: number
  }): Promise<{
    success: boolean
    html_content: string
    template_data: any
  }> => {
    const { data: response } = await api.post('/email/preview', data)
    return response
  },

  sendEmail: async (data: {
    to_email: string
    subject: string
    author_name: string
    paper_title: string
    paper_venue?: string
    paper_year?: number
    paper_citations?: number
  }): Promise<{
    success: boolean
    message: string
    to_email: string
    subject: string
    error?: string
  }> => {
    const { data: response } = await api.post('/email/send', data)
    return response
  },

  getEmailConfig: async (): Promise<{
    valid: boolean
    message: string
    email_address?: string
    smtp_server?: string
    error?: string
  }> => {
    const { data } = await api.get('/email/config')
    return data
  },
}


export default api