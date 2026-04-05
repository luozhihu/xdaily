'use client';

import { MessageSquare, Clock } from 'lucide-react';
import styles from './BriefingCard.module.css';

interface Briefing {
  id: string;
  source: string;
  sourceIcon: string;
  date: string;
  title: string;
  bullets: string[];
  tweetCount: number;
  readTime: string;
}

interface BriefingCardProps {
  briefing: Briefing;
  index: number;
}

export default function BriefingCard({ briefing, index }: BriefingCardProps) {
  const formattedDate = new Date(briefing.date).toLocaleDateString('zh-CN', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });

  return (
    <article
      className={styles.card}
      style={{ animationDelay: `${index * 100}ms` }}
    >
      <header className={styles.header}>
        <div className={styles.source}>
          {briefing.sourceIcon && (
            <img
              src={briefing.sourceIcon}
              alt=""
              className={styles.sourceIcon}
            />
          )}
          <span className={styles.sourceName}>{briefing.source}</span>
        </div>
        <time className={styles.date} dateTime={briefing.date}>
          {formattedDate}
        </time>
      </header>

      <h3 className={styles.title}>{briefing.title}</h3>

      <ul className={styles.bullets}>
        {briefing.bullets.map((bullet, i) => (
          <li key={i} className={styles.bullet}>
            <span className={styles.bulletDot} />
            <span>{bullet}</span>
          </li>
        ))}
      </ul>

      <footer className={styles.footer}>
        <div className={styles.stat}>
          <MessageSquare size={14} />
          <span>{briefing.tweetCount} tweets</span>
        </div>
        <div className={styles.stat}>
          <Clock size={14} />
          <span>{briefing.readTime} read</span>
        </div>
      </footer>
    </article>
  );
}
