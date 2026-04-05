'use client';

import { User } from 'lucide-react';
import styles from './MemberCard.module.css';

interface Member {
  id: string;
  name: string;
  handle: string;
  followers: string;
  bio: string;
  avatar: string;
  isActive: boolean;
}

interface MemberCardProps {
  member: Member;
  stackIndex: number;
  total: number;
}

export default function MemberCard({ member, stackIndex, total }: MemberCardProps) {
  const offset = stackIndex * 8;
  const scale = 1 - (stackIndex * 0.03);
  const zIndex = total - stackIndex;

  return (
    <div
      className={`${styles.card} ${member.isActive ? styles.cardActive : ''}`}
      style={{
        transform: `translateY(${offset}px) scale(${scale})`,
        zIndex,
      }}
    >
      <div className={styles.cardInner}>
        <div className={styles.avatarWrapper}>
          {member.avatar ? (
            <img
              src={member.avatar}
              alt={member.name}
              className={styles.avatar}
              onError={(e) => {
                e.currentTarget.style.display = 'none';
                e.currentTarget.nextElementSibling?.classList.add(styles.avatarFallbackVisible);
              }}
            />
          ) : null}
          <div className={styles.avatarFallback}>
            <User size={24} />
          </div>
        </div>

        <div className={styles.content}>
          <div className={styles.header}>
            <div className={styles.nameGroup}>
              <h3 className={styles.name}>{member.name}</h3>
              <span className={styles.handle}>{member.handle}</span>
            </div>
            <span className={styles.followers}>{member.followers}</span>
          </div>
          <p className={styles.bio}>{member.bio}</p>
        </div>

        {member.isActive && (
          <div className={styles.activeIndicator}>
            <span className={styles.activeDot} />
          </div>
        )}
      </div>
    </div>
  );
}
