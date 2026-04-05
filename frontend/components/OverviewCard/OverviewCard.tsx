'use client';

import { MessageSquare } from 'lucide-react';
import styles from './OverviewCard.module.css';

interface OverviewSummary {
  category_id: number;
  category_name?: string;
  categoryId?: number;
  categoryName?: string;
  categoryIcon?: string;
  summary_date?: string;
  summary_date_display?: string;
  date?: string;
  summary_text?: string;
  summary?: string;
  tweets_count?: number;
  tweetCount?: number;
}

interface OverviewCardProps {
  overview: OverviewSummary;
  index: number;
}

export default function OverviewCard({ overview, index }: OverviewCardProps) {
  const dateStr = overview.summary_date || overview.date || '';
  const displayDate = dateStr ? new Date(dateStr).toLocaleDateString('zh-CN', {
    month: 'short',
    day: 'numeric',
  }) : '';

  const categoryName = overview.category_name || overview.categoryName || '';
  const summaryText = overview.summary_text || overview.summary || '';
  const tweetCount = overview.tweets_count ?? overview.tweetCount ?? 0;

  // Extract first 100 chars as preview
  const summaryPreview = summaryText.length > 150
    ? summaryText.substring(0, 150) + '...'
    : summaryText;

  return (
    <article
      className={styles.card}
      style={{ animationDelay: `${index * 100}ms` }}
    >
      <header className={styles.header}>
        <div className={styles.categoryInfo}>
          <span className={styles.categoryIcon}>{overview.categoryIcon || '📋'}</span>
          <span className={styles.categoryName}>{categoryName}</span>
        </div>
        {displayDate && (
          <time className={styles.date} dateTime={dateStr}>
            {displayDate}
          </time>
        )}
      </header>

      <p className={styles.summary}>{summaryPreview}</p>

      <footer className={styles.footer}>
        <div className={styles.stat}>
          <MessageSquare size={14} />
          <span>{tweetCount} 条推文</span>
        </div>
      </footer>
    </article>
  );
}
