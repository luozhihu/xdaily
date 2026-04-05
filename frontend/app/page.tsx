'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/components/AuthProvider';
import { api } from '@/lib/api';
import Sidebar from '@/components/Sidebar/Sidebar';
import OverviewCard from '@/components/OverviewCard/OverviewCard';
import { X, Plus, Edit2, Trash2, ChevronDown, ChevronUp } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import styles from './page.module.css';

// Types
type MainView = 'control' | 'overview' | 'categoryDetail';

interface Feed {
  id: number;
  name: string;
  twitter_username: string;
  category_id: number;
  tweets_count: number;
  enabled: boolean;
  avatar_url?: string;
  description?: string;
  followers_count?: number;
}

interface ApiCategory {
  id: number;
  name: string;
  description?: string;
  sort_order?: number;
  created_at?: string;
}

interface TwitterUser {
  id: string;
  username: string;
  display_name: string;
  description?: string;
  followers_count?: number;
  following_count?: number;
  tweet_count?: number;
  profile_image_url?: string;
  verified?: boolean;
}

export default function Home() {
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuth();
  const [mainView, setMainView] = useState<MainView>('overview');
  const [categories, setCategories] = useState<ApiCategory[]>([]);
  const [feeds, setFeeds] = useState<Feed[]>([]);
  const [expandedCategories, setExpandedCategories] = useState<Set<number>>(new Set());
  const [selectedCategoryId, setSelectedCategoryId] = useState<number | null>(null);
  const [summaries, setSummaries] = useState<any[]>([]);
  const [todaySummaries, setTodaySummaries] = useState<any[]>([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSummaryModalOpen, setIsSummaryModalOpen] = useState(false);
  const [selectedSummary, setSelectedSummary] = useState<any>(null);
  const [feedsStackHovered, setFeedsStackHovered] = useState(false);
  const [editingCategory, setEditingCategory] = useState<ApiCategory | null>(null);
  const [categoryName, setCategoryName] = useState('');
  const [categoryDesc, setCategoryDesc] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  // Add Feed Modal State
  const [isAddFeedModalOpen, setIsAddFeedModalOpen] = useState(false);
  const [addFeedCategoryId, setAddFeedCategoryId] = useState<number | null>(null);
  const [twitterHandle, setTwitterHandle] = useState('');
  const [twitterUser, setTwitterUser] = useState<TwitterUser | null>(null);
  const [isSearchingTwitter, setIsSearchingTwitter] = useState(false);
  const [twitterSearchError, setTwitterSearchError] = useState('');
  const [isAddingFeed, setIsAddingFeed] = useState(false);

  // Shuffle array helper
  const shuffleArray = <T,>(array: T[]): T[] => {
    const shuffled = [...array];
    for (let i = shuffled.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
    }
    return shuffled;
  };

  // Generate random rotation for card stacking
  const getCardRotation = (index: number, total: number): number => {
    if (index === 0) {
      // Top card: within 20 degrees
      return (Math.random() - 0.5) * 40; // -20 to 20
    }
    // Other cards: random rotation up to 45 degrees in each direction
    return (Math.random() - 0.5) * 90; // -45 to 45
  };

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isLoading, isAuthenticated, router]);

  useEffect(() => {
    if (isAuthenticated && mainView === 'control') {
      fetchCategories();
      fetchFeeds();
    }
  }, [isAuthenticated, mainView]);

  const fetchCategories = async () => {
    try {
      const data = await api.categories.list();
      setCategories(data);
    } catch (err: any) {
      console.error('Failed to fetch categories:', err);
    }
  };

  const fetchFeeds = async () => {
    try {
      const data = await api.feeds.list();
      setFeeds(data);
    } catch (err: any) {
      console.error('Failed to fetch feeds:', err);
    }
  };

  const fetchSummaries = async (categoryId: number) => {
    try {
      const data = await api.summaries.getByCategory(categoryId);
      setSummaries(data || []);
    } catch (err: any) {
      console.error('Failed to fetch summaries:', err);
      setSummaries([]);
    }
  };

  const fetchTodaySummaries = async () => {
    try {
      const today = new Date().toISOString().split('T')[0];
      const data = await api.summaries.getByDate(today);
      setTodaySummaries(data || []);
    } catch (err: any) {
      console.error('Failed to fetch today summaries:', err);
      setTodaySummaries([]);
    }
  };

  useEffect(() => {
    if (isAuthenticated) {
      fetchCategories();
    }
  }, [isAuthenticated]);

  useEffect(() => {
    if (isAuthenticated && mainView === 'overview') {
      fetchTodaySummaries();
    }
  }, [isAuthenticated, mainView]);

  const handleCategorySelect = (categoryId: number) => {
    setSelectedCategoryId(categoryId);
    setMainView('categoryDetail');
    fetchSummaries(categoryId);
  };

  const toggleCategory = (categoryId: number) => {
    setExpandedCategories(prev => {
      const next = new Set(prev);
      if (next.has(categoryId)) {
        next.delete(categoryId);
      } else {
        next.add(categoryId);
      }
      return next;
    });
  };

  const getFeedsByCategory = (categoryId: number) => {
    return feeds.filter(f => f.category_id === categoryId);
  };

  const handleOpenAdd = () => {
    setEditingCategory(null);
    setCategoryName('');
    setCategoryDesc('');
    setError('');
    setIsModalOpen(true);
  };

  const handleOpenEdit = (cat: ApiCategory) => {
    setEditingCategory(cat);
    setCategoryName(cat.name || '');
    setCategoryDesc(cat.description || '');
    setError('');
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setEditingCategory(null);
    setCategoryName('');
    setCategoryDesc('');
    setError('');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!categoryName.trim()) {
      setError('分类名称不能为空');
      return;
    }

    setIsSubmitting(true);
    setError('');

    try {
      if (editingCategory) {
        await api.categories.update(editingCategory.id, categoryName.trim(), categoryDesc.trim());
      } else {
        await api.categories.create(categoryName.trim(), categoryDesc.trim());
      }
      await fetchCategories();
      handleCloseModal();
    } catch (err: any) {
      setError(err.message || '操作失败');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async (id: number) => {
    const category = categories.find(c => c.id === id);
    const feedCount = feeds.filter(f => f.category_id === id).length;
    const message = feedCount > 0
      ? `确定要删除"${category?.name}"吗？\n\n该操作会同时删除该分类下的 ${feedCount} 个博主。`
      : `确定要删除"${category?.name}"吗？`;
    if (!confirm(message)) return;

    try {
      await api.categories.delete(id);
      await fetchCategories();
    } catch (err: any) {
      alert(err.message || '删除失败');
    }
  };

  const handleOpenAddFeed = (categoryId: number) => {
    setAddFeedCategoryId(categoryId);
    setTwitterHandle('');
    setTwitterUser(null);
    setTwitterSearchError('');
    setIsAddFeedModalOpen(true);
  };

  const handleCloseAddFeedModal = () => {
    setIsAddFeedModalOpen(false);
    setAddFeedCategoryId(null);
    setTwitterHandle('');
    setTwitterUser(null);
    setTwitterSearchError('');
  };

  const handleSearchTwitter = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!twitterHandle.trim()) return;

    const handle = twitterHandle.trim().replace('@', '');
    setIsSearchingTwitter(true);
    setTwitterSearchError('');
    setTwitterUser(null);

    try {
      const user = await api.twitter.getUserInfo(handle);
      setTwitterUser(user);
    } catch (err: any) {
      setTwitterSearchError(err.message || '未找到该用户');
    } finally {
      setIsSearchingTwitter(false);
    }
  };

  const handleAddFeed = async () => {
    if (!twitterUser || !addFeedCategoryId) return;

    setIsAddingFeed(true);
    try {
      await api.feeds.create({
        name: twitterUser.display_name,
        twitter_username: twitterUser.username,
        category_id: addFeedCategoryId,
        description: twitterUser.description,
        avatar_url: twitterUser.profile_image_url,
        followers_count: twitterUser.followers_count,
      });
      await fetchFeeds();
      handleCloseAddFeedModal();
    } catch (err: any) {
      alert(err.message || '添加失败');
    } finally {
      setIsAddingFeed(false);
    }
  };

  const handleDeleteFeed = async (feedId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('确定要删除该博主吗？')) return;

    try {
      await api.feeds.delete(feedId);
      await fetchFeeds();
    } catch (err: any) {
      alert(err.message || '删除失败');
    }
  };

  if (isLoading) {
    return (
      <div className={styles.loading}>
        <div className={styles.spinner} />
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className={styles.container}>
      <Sidebar
        categories={categories}
        mainView={mainView}
        onMainViewChange={setMainView}
        onCategorySelect={handleCategorySelect}
        selectedCategoryId={selectedCategoryId}
      />
      <main className={styles.main}>
        {mainView === 'control' ? (
          <section className={styles.managementSection}>
            <header className={styles.managementHeader}>
              <h2 className={styles.managementTitle}>控制台</h2>
              <button className={styles.addBtnHeader} onClick={handleOpenAdd}>
                <Plus size={16} />
                添加分类
              </button>
            </header>

            <div className={styles.categoryListContainer}>
              {categories.map(cat => {
                const categoryFeeds = getFeedsByCategory(cat.id);
                const isExpanded = expandedCategories.has(cat.id);

                return (
                  <div key={cat.id} className={styles.categoryExpandCard}>
                    {/* Card Header - Always visible */}
                    <div
                      className={styles.categoryExpandHeader}
                      onClick={() => toggleCategory(cat.id)}
                    >
                      <div className={styles.categoryExpandInfo}>
                        <span className={styles.categoryExpandIcon}>📁</span>
                        <div className={styles.categoryExpandText}>
                          <span className={styles.categoryExpandName}>{cat.name}</span>
                          {!isExpanded && cat.description && (
                            <span className={styles.categoryExpandDesc}>
                              {cat.description.length > 40 ? cat.description.substring(0, 40) + '...' : cat.description}
                            </span>
                          )}
                          {isExpanded && cat.description && (
                            <span className={styles.categoryExpandDescFull}>{cat.description}</span>
                          )}
                        </div>
                      </div>
                      <div className={styles.categoryExpandActions}>
                        <span className={styles.feedCount}>{categoryFeeds.length} 个博主</span>
                        <button
                          className={styles.expandBtn}
                          onClick={(e) => {
                            e.stopPropagation();
                            toggleCategory(cat.id);
                          }}
                          title={isExpanded ? '收起' : '展开'}
                        >
                          {isExpanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                        </button>
                        <button
                          className={styles.iconBtn}
                          onClick={(e) => {
                            e.stopPropagation();
                            handleOpenEdit(cat);
                          }}
                          title="编辑"
                        >
                          <Edit2 size={16} />
                        </button>
                        <button
                          className={`${styles.iconBtn} ${styles.deleteBtn}`}
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDelete(cat.id);
                          }}
                          title="删除"
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </div>

                    {/* Expanded Content */}
                    {isExpanded && (
                      <div className={styles.feedCardsContainer}>
                        <div className={styles.feedCardsStack}>
                          {/* Add Feed Card */}
                          <button
                            className={styles.addFeedCard}
                            onClick={() => handleOpenAddFeed(cat.id)}
                          >
                            <Plus size={20} />
                            <span>添加博主</span>
                          </button>
                          {/* Feed Cards */}
                          {categoryFeeds.map((feed) => (
                            <div
                              key={feed.id}
                              className={styles.feedMiniCard}
                            >
                              <img
                                src={feed.avatar_url || `https://ui-avatars.com/api/?name=${encodeURIComponent(feed.name)}&background=6366f1&color=fff`}
                                alt=""
                                className={styles.feedMiniAvatar}
                              />
                              <div className={styles.feedMiniInfo}>
                                <span className={styles.feedMiniName}>{feed.name}</span>
                                <span className={styles.feedMiniHandle}>@{feed.twitter_username}</span>
                                {feed.followers_count !== undefined && feed.followers_count > 0 && (
                                  <span className={styles.feedMiniFollowers}>
                                    {feed.followers_count >= 1000000
                                  ? `${(feed.followers_count / 1000000).toFixed(1)}M`
                                  : feed.followers_count >= 10000
                                    ? `${(feed.followers_count / 10000).toFixed(1)}W`
                                    : feed.followers_count >= 1000
                                      ? `${(feed.followers_count / 1000).toFixed(1)}K`
                                      : feed.followers_count.toLocaleString()} followers
                                  </span>
                                )}
                              </div>
                              <button
                                className={`${styles.iconBtn} ${styles.deleteBtn}`}
                                onClick={(e) => handleDeleteFeed(feed.id, e)}
                                title="删除"
                              >
                                <Trash2 size={14} />
                              </button>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}

              {categories.length === 0 && (
                <div className={styles.emptyState}>
                  <p>暂无分类，点击上方按钮添加</p>
                </div>
              )}
            </div>
          </section>
        ) : mainView === 'categoryDetail' ? (
          <section className={styles.categoryDetailSection}>
            {selectedCategoryId && (() => {
              const category = categories.find(c => c.id === selectedCategoryId);
              const categoryFeeds = feeds.filter(f => f.category_id === selectedCategoryId);
              return category ? (
                <>
                  {/* Category Header */}
                  <header className={styles.categoryDetailHeader}>
                    <div className={styles.categoryDetailInfo}>
                      <h2 className={styles.categoryDetailTitle}>{category.name}</h2>
                      {category.description && (
                        <p className={styles.categoryDetailDesc}>{category.description}</p>
                      )}
                    </div>
                    <button
                      className={styles.backBtn}
                      onClick={() => setMainView('control')}
                    >
                      返回
                    </button>
                  </header>

                  {/* Feeds Section */}
                  <div className={styles.categoryDetailSection}>
                    <h3 className={styles.categoryDetailSectionTitle}>群组成员 ({categoryFeeds.length})</h3>
                    <div
                      className={styles.feedCardsStack}
                      onMouseEnter={() => setFeedsStackHovered(true)}
                      onMouseLeave={() => setFeedsStackHovered(false)}
                    >
                      {(() => {
                        const shuffledFeeds = shuffleArray(categoryFeeds);
                        return shuffledFeeds.map((feed, index) => {
                          const rotation = feedsStackHovered ? 0 : getCardRotation(index, shuffledFeeds.length);
                          const spreadOffset = feedsStackHovered ? 0 : (index === 0 ? 0 : -80 - index * 20);
                          return (
                            <div
                              key={feed.id}
                              className={styles.feedMiniCard}
                              style={{
                                transform: `rotate(${rotation}deg) translateY(${feedsStackHovered ? 0 : `${-index * 8}px`})`,
                                zIndex: shuffledFeeds.length - index,
                                marginLeft: index === 0 ? 0 : feedsStackHovered ? `${index * 30}px` : `${-100 - index * 30}px`,
                                transition: 'all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1)',
                              }}
                            >
                              <img
                                src={feed.avatar_url || `https://ui-avatars.com/api/?name=${encodeURIComponent(feed.name)}&background=6366f1&color=fff`}
                                alt=""
                                className={styles.feedMiniAvatar}
                              />
                              <div className={styles.feedMiniInfo}>
                                <span className={styles.feedMiniName}>{feed.name}</span>
                                <span className={styles.feedMiniHandle}>@{feed.twitter_username}</span>
                                {feed.description && (
                                  <span className={styles.feedMiniDesc}>{feed.description}</span>
                                )}
                                {feed.followers_count !== undefined && feed.followers_count > 0 && (
                                  <span className={styles.feedMiniFollowers}>
                                    {feed.followers_count >= 1000000
                                      ? `${(feed.followers_count / 1000000).toFixed(1)}M`
                                      : feed.followers_count >= 10000
                                        ? `${(feed.followers_count / 10000).toFixed(1)}W`
                                        : feed.followers_count >= 1000
                                          ? `${(feed.followers_count / 1000).toFixed(1)}K`
                                          : feed.followers_count.toLocaleString()} followers
                                  </span>
                                )}
                              </div>
                            </div>
                          );
                        });
                      })()}
                    </div>
                  </div>

                  {/* Summaries Section */}
                  <div className={styles.categoryDetailSection}>
                    <h3 className={styles.categoryDetailSectionTitle}>历史简报</h3>
                    <div className={styles.summariesList}>
                      {summaries.length === 0 ? (
                        <p className={styles.emptyText}>暂无简报</p>
                      ) : (
                        summaries.map((summary) => {
                          const previewText = summary.summary_text?.length > 80
                            ? summary.summary_text.substring(0, 80) + '...'
                            : summary.summary_text;
                          return (
                            <div
                              key={summary.id}
                              className={styles.summaryCard}
                              onClick={() => {
                                setSelectedSummary(summary);
                                setIsSummaryModalOpen(true);
                              }}
                              style={{ cursor: 'pointer' }}
                            >
                              <div className={styles.summaryCardHeader}>
                                <span className={styles.summaryDate}>{summary.summary_date}</span>
                                <span className={styles.summaryTweetCount}>{summary.tweets_count} 条推文</span>
                              </div>
                              <div className={styles.summaryText}>
                                <ReactMarkdown>{previewText}</ReactMarkdown>
                              </div>
                              {summary.summary_text?.length > 80 && (
                                <span className={styles.expandHint}>点击查看全文</span>
                              )}
                            </div>
                          );
                        })
                      )}
                    </div>
                  </div>
                </>
              ) : null;
            })()}
          </section>
        ) : (
          <section className={styles.overviewSection}>
            <header className={styles.sectionHeader}>
              <h2 className={styles.sectionTitle}>当日总览</h2>
              <span className={styles.sectionSubtitle}>每日总览</span>
            </header>
            <div className={styles.summariesGrid}>
              {todaySummaries.map((summary, index) => (
                <div
                  key={summary.id || summary.category_id}
                  onClick={() => {
                    setSelectedSummary(summary);
                    setIsSummaryModalOpen(true);
                  }}
                  style={{ cursor: 'pointer' }}
                >
                  <OverviewCard
                    overview={summary}
                    index={index}
                  />
                </div>
              ))}
            </div>
          </section>
        )}
      </main>

      {/* Edit/Create Modal */}
      {isModalOpen && (
        <div className={styles.modalOverlay} onClick={handleCloseModal}>
          <div className={styles.modal} onClick={e => e.stopPropagation()}>
            <div className={styles.modalHeader}>
              <h3>{editingCategory ? '编辑分类' : '添加分类'}</h3>
              <button className={styles.closeBtn} onClick={handleCloseModal}>
                <X size={20} />
              </button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className={styles.formField}>
                <label>分类名称</label>
                <input
                  type="text"
                  value={categoryName}
                  onChange={e => setCategoryName(e.target.value)}
                  placeholder="输入分类名称"
                  autoFocus
                />
              </div>
              <div className={styles.formField}>
                <label>分类介绍</label>
                <textarea
                  value={categoryDesc}
                  onChange={e => setCategoryDesc(e.target.value)}
                  placeholder="输入分类介绍（可选）"
                  rows={3}
                />
              </div>
              {error && <div className={styles.formError}>{error}</div>}
              <div className={styles.modalActions}>
                <button type="button" className={styles.cancelBtn} onClick={handleCloseModal}>
                  取消
                </button>
                <button type="submit" className={styles.submitBtn} disabled={isSubmitting}>
                  {isSubmitting ? '保存中...' : '保存'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add Feed Modal */}
      {isAddFeedModalOpen && (
        <div className={styles.modalOverlay} onClick={handleCloseAddFeedModal}>
          <div className={styles.modal} onClick={e => e.stopPropagation()}>
            <div className={styles.modalHeader}>
              <h3>添加博主</h3>
              <button className={styles.closeBtn} onClick={handleCloseAddFeedModal}>
                <X size={20} />
              </button>
            </div>
            <form onSubmit={handleSearchTwitter}>
              <div className={styles.formField}>
                <label>Twitter Handle</label>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <input
                    type="text"
                    value={twitterHandle}
                    onChange={e => setTwitterHandle(e.target.value)}
                    placeholder="输入用户名（如 elonmusk）"
                    autoFocus
                  />
                  <button
                    type="submit"
                    className={styles.submitBtn}
                    disabled={isSearchingTwitter}
                    style={{ whiteSpace: 'nowrap' }}
                  >
                    {isSearchingTwitter ? '搜索中...' : '搜索'}
                  </button>
                </div>
              </div>
              {twitterSearchError && (
                <div className={styles.formError}>{twitterSearchError}</div>
              )}
            </form>

            {twitterUser && (
              <div className={styles.twitterUserCard}>
                <img
                  src={twitterUser.profile_image_url?.replace('_normal.', '_400x400.') || `https://ui-avatars.com/api/?name=${encodeURIComponent(twitterUser.display_name)}&background=6366f1&color=fff`}
                  alt=""
                  className={styles.feedMiniAvatar}
                />
                <div className={styles.feedMiniInfo}>
                  <span className={styles.feedMiniName}>{twitterUser.display_name}</span>
                  <span className={styles.feedMiniHandle}>@{twitterUser.username}</span>
                  {twitterUser.description && (
                    <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                      {twitterUser.description.length > 80 ? twitterUser.description.substring(0, 80) + '...' : twitterUser.description}
                    </p>
                  )}
                  {twitterUser.followers_count !== undefined && (
                    <p style={{ fontSize: '0.6875rem', color: 'var(--text-tertiary)', marginTop: '4px' }}>
                      {twitterUser.followers_count.toLocaleString()} 粉丝
                    </p>
                  )}
                </div>
              </div>
            )}

            {twitterUser && (
              <div className={styles.modalActions}>
                <button
                  type="button"
                  className={styles.cancelBtn}
                  onClick={handleCloseAddFeedModal}
                >
                  取消
                </button>
                <button
                  type="button"
                  className={styles.submitBtn}
                  onClick={handleAddFeed}
                  disabled={isAddingFeed}
                >
                  {isAddingFeed ? '添加中...' : '添加'}
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Summary Detail Modal */}
      {isSummaryModalOpen && selectedSummary && (
        <div className={styles.modalOverlay} onClick={() => setIsSummaryModalOpen(false)}>
          <div className={styles.modal} onClick={e => e.stopPropagation()} style={{ maxWidth: '800px', width: '90vw' }}>
            <div className={styles.modalHeader}>
              <h3>{selectedSummary.summary_date} 简报</h3>
              <button className={styles.closeBtn} onClick={() => setIsSummaryModalOpen(false)}>
                <X size={20} />
              </button>
            </div>
            <div style={{ marginBottom: 'var(--space-4)' }}>
              <span className={styles.summaryTweetCount}>{selectedSummary.tweets_count} 条推文</span>
            </div>
            <div style={{ maxHeight: '70vh', overflowY: 'auto' }} className={styles.modalMarkdown}>
              <ReactMarkdown>{selectedSummary.summary_text || ''}</ReactMarkdown>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
