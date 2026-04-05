'use client';

import { useRouter } from 'next/navigation';
import { useTheme } from '@/components/ThemeProvider';
import { useAuth } from '@/components/AuthProvider';
import { LogOut, Moon, Sun, LayoutDashboard, CalendarDays } from 'lucide-react';
import styles from './Sidebar.module.css';

interface SidebarProps {
  categories: any[];
  mainView: 'control' | 'overview' | 'categoryDetail';
  onMainViewChange: (view: 'control' | 'overview' | 'categoryDetail') => void;
  onCategorySelect?: (categoryId: number) => void;
  selectedCategoryId?: number | null;
}

export default function Sidebar({ categories, mainView, onMainViewChange, onCategorySelect, selectedCategoryId }: SidebarProps) {
  const router = useRouter();
  const { theme, toggleTheme } = useTheme();
  const { user, logout } = useAuth();

  const handleLogout = () => {
    logout();
    router.push('/login');
  };

  return (
    <aside className={styles.sidebar}>
      {/* Logo */}
      <div className={styles.logo}>
        <div className={styles.logoIcon}>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <rect x="3" y="3" width="18" height="18" rx="4" fill="url(#logoGradient)" />
            <path
              d="M8 12h8M12 8v8"
              stroke="white"
              strokeWidth="2"
              strokeLinecap="round"
            />
            <defs>
              <linearGradient id="logoGradient" x1="3" y1="3" x2="21" y2="21">
                <stop stopColor="#6366F1" />
                <stop offset="1" stopColor="#8B5CF6" />
              </linearGradient>
            </defs>
          </svg>
        </div>
        <span className={styles.logoText}>每日简报</span>
      </div>

      {/* Navigation */}
      <nav className={styles.nav}>
        <button
          className={`${styles.navItem} ${mainView === 'control' ? styles.navItemActive : ''}`}
          onClick={() => onMainViewChange('control')}
        >
          <LayoutDashboard size={18} strokeWidth={1.75} />
          <span>控制台</span>
        </button>
        <button
          className={`${styles.navItem} ${mainView === 'overview' ? styles.navItemActive : ''}`}
          onClick={() => onMainViewChange('overview')}
        >
          <CalendarDays size={18} strokeWidth={1.75} />
          <span>当日总览</span>
        </button>
      </nav>

      {/* Categories Section */}
      <div className={styles.groupsSection}>
        <div className={styles.groupsHeader}>
          <span className={styles.groupsTitle}>分类</span>
        </div>
        <div className={styles.groupsList}>
          {categories.map((category) => (
            <button
              key={category.id}
              className={`${styles.groupItem} ${selectedCategoryId === category.id ? styles.groupItemActive : ''}`}
              onClick={() => onCategorySelect?.(category.id)}
            >
              <span>{category.name}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Bottom Section */}
      <div className={styles.bottom}>
        {/* Toggles */}
        <div className={styles.toggles}>
          <button className={styles.toggle} onClick={toggleTheme}>
            {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
          </button>
          <button className={styles.toggle} onClick={handleLogout}>
            <LogOut size={16} />
          </button>
        </div>

        {/* User Profile */}
        <div className={styles.profile}>
          <div className={styles.avatar}>
            <span>{user?.username?.charAt(0).toUpperCase() || 'U'}</span>
          </div>
          <div className={styles.profileInfo}>
            <span className={styles.profileName}>{user?.username || '用户'}</span>
            <span className={styles.profileRole}>{user?.role === 'admin' ? '管理员' : '用户'}</span>
          </div>
        </div>
      </div>
    </aside>
  );
}
