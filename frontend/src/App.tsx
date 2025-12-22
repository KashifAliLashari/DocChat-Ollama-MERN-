import { useEffect, useMemo, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { ArrowUpRight, Book, MessageSquare, Plus, Square } from 'lucide-react'
import './App.css'

type DocumentRecord = {
  id: string
  name: string
  path: string
  created_at: string
}

type ConversationRecord = {
  id: string
  title: string
  created_at: string
}

type MessageRecord = {
  id: string
  conversation_id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

type UploadDocumentResponse = {
  document_id: string
  name: string
  path: string
}

type AttachmentInfo = {
  name: string
  id: string
}

type ViewMode = 'chats' | 'docs' | 'chat'
const API_BASE =
  import.meta.env.VITE_API_BASE?.replace(/\/$/, '') ?? 'http://127.0.0.1:8000'

const FileTextIcon = ({ size = 16 }: { size?: number }) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M6 22a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.704.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2z" />
    <path d="M14 2v5a1 1 0 0 0 1 1h5" />
    <path d="M10 9H8" />
    <path d="M16 13H8" />
    <path d="M16 17H8" />
  </svg>
)

const PencilIcon = ({ size = 14 }: { size?: number }) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    className="lucide lucide-pencil-icon"
  >
    <path d="M21.174 6.812a1 1 0 0 0-3.986-3.987L3.842 16.174a2 2 0 0 0-.5.83l-1.321 4.352a.5.5 0 0 0 .623.622l4.353-1.32a2 2 0 0 0 .83-.497z" />
    <path d="m15 5 4 4" />
  </svg>
)

const TrashIcon = ({ size = 16 }: { size?: number }) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    className="lucide lucide-trash-icon"
  >
    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" />
    <path d="M3 6h18" />
    <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
  </svg>
)

const PanelOpenIcon = ({ size = 18 }: { size?: number }) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <rect width="18" height="18" x="3" y="3" rx="2" />
    <path d="M15 3v18" />
    <path d="m10 15-3-3 3-3" />
  </svg>
)

const PanelCloseIcon = ({ size = 18 }: { size?: number }) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <rect width="18" height="18" x="3" y="3" rx="2" />
    <path d="M15 3v18" />
    <path d="m8 9 3 3-3 3" />
  </svg>
)

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init)
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || `Request failed: ${res.status}`)
  }
  return (await res.json()) as T
}

function App() {
  const [docs, setDocs] = useState<DocumentRecord[]>([])
  const [conversations, setConversations] = useState<ConversationRecord[]>([])
  const [messages, setMessages] = useState<MessageRecord[]>([])
  const [uploadError, setUploadError] = useState<string | null>(null)

  const [conversationId, setConversationId] = useState<string>(() => crypto.randomUUID())
  const [message, setMessage] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [chatError, setChatError] = useState<string | null>(null)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [viewMode, setViewMode] = useState<ViewMode>('chat')
  const [streamingText, setStreamingText] = useState('')
  const [uploadedFileName, setUploadedFileName] = useState<string | null>(null)
  const [uploadedDocumentId, setUploadedDocumentId] = useState<string | null>(null)
  const [lastUsedFileName, setLastUsedFileName] = useState<string | null>(null)
  const [lastUsedDocumentId, setLastUsedDocumentId] = useState<string | null>(null)
  const [conversationAttachments, setConversationAttachments] = useState<
    Record<string, AttachmentInfo>
  >({})
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editingText, setEditingText] = useState('')
  const abortRef = useRef<AbortController | null>(null)
  const fileInputRef = useRef<HTMLInputElement | null>(null)

  const apiDocsUrl = useMemo(() => `${API_BASE}/documents`, [])
  const apiConversationsUrl = useMemo(() => `${API_BASE}/conversations`, [])
  const apiUploadUrl = useMemo(() => `${API_BASE}/documents/upload`, [])
  const apiChatUrl = useMemo(() => `${API_BASE}/chat/stream`, [])

  useEffect(() => {
    // Always land in a fresh chat on load/refresh
    handleNewChat()
    window.history.replaceState({}, '', '/chats')

    const onPop = () => {
      handleNewChat()
      window.history.replaceState({}, '', '/chats')
    }
    window.addEventListener('popstate', onPop)
    return () => window.removeEventListener('popstate', onPop)
  }, [])

  useEffect(() => {
    void refreshDocs()
    void refreshConversations()
  }, [])

  const attachmentForConversation = (id: string): AttachmentInfo | undefined =>
    conversationAttachments[id]

  async function refreshDocs() {
    try {
      const list = await fetchJson<DocumentRecord[]>(apiDocsUrl)
      setDocs(list)
    } catch (err) {
      console.error('Failed to fetch documents', err)
    }
  }

  async function refreshConversations() {
    try {
      const list = await fetchJson<ConversationRecord[]>(apiConversationsUrl)
      setConversations(list)
    } catch (err) {
      console.error('Failed to fetch conversations', err)
    }
  }

  async function loadMessages(convId: string) {
    try {
      const list = await fetchJson<MessageRecord[]>(
        `${API_BASE}/conversations/${convId}/messages`
      )
      setMessages(list)
    } catch (err) {
      console.error('Failed to fetch messages', err)
    }
  }

  function handleNewChat() {
    const newId = crypto.randomUUID()
    setConversationId(newId)
    setMessage('')
    setMessages([])
    setStreamingText('')
    setUploadedFileName(null)
    setUploadedDocumentId(null)
    setLastUsedFileName(null)
    setLastUsedDocumentId(null)
    setChatError(null)
    setViewMode('chat')
  }

  async function handleSelectConversation(id: string) {
    setConversationId(id)
    setViewMode('chat')
    setMessage('')
    setStreamingText('')
    const existing = attachmentForConversation(id)
    if (existing) {
      setUploadedFileName(existing.name)
      setUploadedDocumentId(existing.id)
      setLastUsedFileName(existing.name)
      setLastUsedDocumentId(existing.id)
    } else {
      setUploadedFileName(null)
      setUploadedDocumentId(null)
    }
    await loadMessages(id)
  }

  async function uploadFile(f: File) {
    const fd = new FormData()
    fd.append('file', f)
    setUploadError(null)
    try {
      const resp = await fetchJson<UploadDocumentResponse>(apiUploadUrl, {
        method: 'POST',
        body: fd,
      })
      await refreshDocs()
      await refreshConversations()
      setUploadedFileName(resp.name)
      setUploadedDocumentId(resp.document_id)
      setLastUsedFileName(resp.name)
      setLastUsedDocumentId(resp.document_id)
      setConversationAttachments((prev) => ({
        ...prev,
        [conversationId]: { name: resp.name, id: resp.document_id },
      }))
    } catch (err) {
      console.error('Upload failed', err)
      setUploadError(String(err))
    }
  }

  function parseSseLines(buffer: string, onEvent: (data: any) => void): string {
    const events = buffer.split('\n\n')
    let carry = events.pop() ?? ''
    for (const evt of events) {
      const line = evt.trim()
      if (line.startsWith('data:')) {
        const payload = line.replace(/^data:\s*/, '')
        if (!payload) continue
        try {
          const parsed = JSON.parse(payload)
          onEvent(parsed)
        } catch (err) {
          console.warn('Failed to parse SSE payload', payload, err)
        }
      }
    }
    return carry
  }

  async function handleChat(e?: FormEvent, override?: string, opts?: { appendUser?: boolean }) {
    if (e) e.preventDefault()
    const textToSend = (override ?? message).trim()
    if (!textToSend || streaming) return

    const convAttachment = attachmentForConversation(conversationId)
    const attachmentName =
      uploadedFileName || convAttachment?.name || lastUsedFileName || undefined
    const attachmentId = uploadedDocumentId || convAttachment?.id || lastUsedDocumentId || undefined

    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    setChatError(null)
    setStreaming(true)
    setStreamingText('')
    setMessage('')
    if (opts?.appendUser !== false) {
      const userMsg: MessageRecord = {
        id: crypto.randomUUID(),
        conversation_id: conversationId,
        role: 'user',
        content: textToSend,
        created_at: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, userMsg])
    }

    try {
      const res = await fetch(apiChatUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'text/event-stream',
        },
        body: JSON.stringify({
          message: textToSend,
          conversation_id: conversationId,
          source_name: attachmentName,
          source_id: attachmentId,
        }),
        signal: controller.signal,
      })
      if (!res.ok || !res.body) {
        throw new Error(`Chat failed: ${res.status}`)
      }
      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      while (true) {
        const { value, done } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        buffer = parseSseLines(buffer, (data) => {
          if (data.token) {
            setStreamingText((prev) => prev + (data.token as string))
          }
        })
      }
      await refreshConversations()
      await loadMessages(conversationId)
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        console.error('Chat failed', err)
        setChatError(
          'Chat failed. Please ensure Ollama is running and the embedding model is available.'
        )
      }
    } finally {
      setStreaming(false)
      setStreamingText('')
      // Keep attachment visible; update last-used so subsequent turns reuse it.
      if (attachmentName) setLastUsedFileName(attachmentName)
      if (attachmentId) setLastUsedDocumentId(attachmentId)
    }
  }

  function handleAbort() {
    abortRef.current?.abort()
    setStreaming(false)
  }

  async function handleDeleteConversation(id: string) {
    try {
      await fetchJson<{ status: string }>(`${API_BASE}/conversations/${id}`, {
        method: 'DELETE',
      })
      if (conversationId === id) {
        handleNewChat()
      }
      await refreshConversations()
    } catch (err) {
      console.error('Failed to delete conversation', err)
      setChatError('Failed to delete conversation')
    }
  }

  return (
    <div className="app-root">
      <div className="app shell">
        <aside className={`sidebar-rail ${sidebarOpen ? 'open' : 'collapsed'}`}>
          <div className="sidebar-top">
            {sidebarOpen && <div className="brand">Offline PDF Chatbot</div>}
            <button
              className="ghost-btn"
              onClick={() => setSidebarOpen((v) => !v)}
              title="Toggle sidebar"
            >
              {sidebarOpen ? <PanelCloseIcon size={18} /> : <PanelOpenIcon size={18} />}
            </button>
          </div>

          <button className="nav-btn primary" onClick={handleNewChat}>
            <Plus size={18} />
            {sidebarOpen && <span>New chat</span>}
          </button>

          <nav className="nav-stack">
            <button
              className="nav-btn"
              onClick={() => {
                setViewMode('chats')
              }}
            >
              <MessageSquare size={18} />
              {sidebarOpen && <span>Chats</span>}
            </button>
            <button
              className="nav-btn"
              onClick={() => {
                setViewMode('docs')
              }}
            >
              <Book size={18} />
              {sidebarOpen && <span>Docs</span>}
            </button>
          </nav>

          <div className="sidebar-section">
            <div className="sidebar-list">
              {conversations.length === 0 ? (
                <p className="muted small">{sidebarOpen ? 'No conversations yet.' : 'No chats'}</p>
              ) : (
                conversations.map((c) => {
                  const isActive = c.id === conversationId
                  return (
                    <div
                      key={c.id}
                      className={`chat-item ${isActive ? 'active' : ''}`}
                      onClick={() => void handleSelectConversation(c.id)}
                      title={c.title || 'Conversation'}
                    >
                      <div className="chat-name">{sidebarOpen ? c.title || 'Conversation' : ''}</div>
                      {sidebarOpen && (
                        <button
                          className="ghost-btn small"
                          onClick={(e) => {
                            e.stopPropagation()
                            handleDeleteConversation(c.id)
                          }}
                          title="Delete conversation"
                        >
                          <TrashIcon />
                        </button>
                      )}
                    </div>
                  )
                })
              )}
            </div>
          </div>

          <div className="sidebar-footer">
            <div className="avatar">K</div>
            {sidebarOpen && (
              <div className="profile">
                <div className="profile-name">Kashif</div>
                <div className="profile-plan">Free plan</div>
              </div>
            )}
          </div>
        </aside>

        <main className="content">
          {viewMode === 'chats' && (
            <div className="list-view card">
              <div className="list-view-header">
                <h1>Chats</h1>
                <button className="new-chat-top" onClick={handleNewChat}>
                  <Plus size={16} />
                  <span>New chat</span>
                </button>
              </div>
              <input className="search" placeholder="Search your chats..." disabled />
              <div className="list-items">
                {conversations.map((c) => (
                  <div
                    key={c.id}
                    className="list-row"
                    onClick={() => void handleSelectConversation(c.id)}
                  >
                    <div className="list-title">{c.title || 'Conversation'}</div>
                    <button
                      className="ghost-btn small"
                      onClick={(e) => {
                        e.stopPropagation()
                        handleDeleteConversation(c.id)
                      }}
                      title="Delete conversation"
                    >
                      ⋯
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {viewMode === 'docs' && (
            <div className="list-view card">
              <div className="list-view-header">
                <h1>Documents</h1>
              </div>
              {uploadError && <div className="alert error">Upload failed: {uploadError}</div>}
              <div className="list-items">
                {docs.length === 0 ? (
                  <p className="muted">No documents yet.</p>
                ) : (
                  docs.map((doc) => (
                    <div key={doc.id} className="list-row">
                      <div className="list-title">{doc.name}</div>
                      <div className="list-sub">{new Date(doc.created_at).toLocaleString()}</div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

          {viewMode === 'chat' && (
            <div className="chat-window">
              {messages.length === 0 && (
                <div className="empty-chat-hint">Start a conversation by typing a message.</div>
              )}
              <div className="messages">
                {messages.map((m) => {
                  const isEditing = editingId === m.id
                  const isUser = m.role === 'user'
                  return (
                    <div key={m.id} className={`msg ${isUser ? 'user' : 'assistant'}`}>
                      <div className="bubble">
                        {isEditing ? (
                          <div className="edit-inline">
                            <textarea
                              value={editingText}
                              onChange={(e) => setEditingText(e.target.value)}
                              rows={3}
                            />
                            <div className="edit-inline-actions">
                              <button
                                type="button"
                                onClick={() => setEditingId(null)}
                                className="edit-cancel"
                              >
                                Cancel
                              </button>
                              <button
                                type="button"
                                onClick={async () => {
                                  if (!editingText.trim()) return
                                  setMessages((prev) =>
                                    prev.map((msg) =>
                                      msg.id === m.id ? { ...msg, content: editingText } : msg
                                    )
                                  )
                                  setEditingId(null)
                                  setEditingText('')
                                  await handleChat(undefined, editingText, { appendUser: false })
                                }}
                                className="edit-save"
                              >
                                Save & Resend
                              </button>
                            </div>
                          </div>
                        ) : (
                          <>
                            {m.content}
                            {isUser && (
                              <button
                                className="edit-btn"
                                type="button"
                                onClick={() => {
                                  setEditingId(m.id)
                                  setEditingText(m.content)
                                }}
                                title="Edit and resend"
                              >
                                <PencilIcon size={14} />
                              </button>
                            )}
                          </>
                        )}
                      </div>
                    </div>
                  )
                })}
                {streamingText && (
                  <div className="msg assistant">
                    <div className="bubble">{streamingText}</div>
                  </div>
                )}
              </div>
              <form className="chat-input" onSubmit={handleChat}>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="application/pdf"
                  hidden
                  onChange={async (e) => {
                    const selected = e.target.files?.[0]
                    if (selected) {
                      await uploadFile(selected)
                      e.target.value = ''
                    }
                  }}
                />
                <div className="chat-controls">
                  <button
                    type="button"
                    className="icon-btn"
                    aria-label="Attach PDF"
                    onClick={() => fileInputRef.current?.click()}
                  >
                    <FileTextIcon size={16} />
                  </button>
                  {uploadedFileName && (
                    <div className="upload-pill" title={uploadedFileName}>
                      <FileTextIcon size={12} />
                      <span className="upload-pill-text">{uploadedFileName}</span>
                      <button
                        type="button"
                        className="icon-btn"
                        onClick={() => {
                          setUploadedFileName(null)
                          setUploadedDocumentId(null)
                        }}
                        aria-label="Clear attachment"
                      >
                        ×
                      </button>
                    </div>
                  )}
                </div>
                <textarea
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  rows={3}
                  placeholder="Type..."
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault()
                      e.currentTarget.form?.requestSubmit()
                    }
                  }}
                />
                <div className="chat-actions">
                  {streaming && (
                    <button type="button" className="icon-btn" onClick={handleAbort} aria-label="Stop">
                      <Square size={16} />
                    </button>
                  )}
                  <button type="submit" className="icon-btn primary" disabled={streaming} aria-label="Send">
                    <ArrowUpRight size={16} />
                  </button>
                </div>
              </form>
              {chatError && <div className="alert error">Chat error: {chatError}</div>}
            </div>
          )}
        </main>
      </div>
    </div>
  )
}

export default App
