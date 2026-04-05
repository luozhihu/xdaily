# Curated Daily 前端设计方案

## 1. Concept & Vision

**Curated Daily (每日简报)** — 一个优雅的 Twitter 内容策展平台，为用户呈现 AI、科技领域 KOL 的精选推文与 AI 生成的历史简报。

设计理念：**"数字发行的精致杂志"** — 融合传统编辑出版物的庄重感与现代数字产品的流畅体验。像翻阅一本精心排版的期刊，同时拥有动态内容和智能功能。

## 2. Design Language

### Aesthetic Direction
**Editorial Minimalism meets Modern SaaS** — 受《纽约时报》数字版和 Linear App 启发的精致克鲁斯风格。大量留白、精确的排版层次、克制的色彩使用，但通过微妙的阴影层次和卡片堆叠效果创造深度。

### Color Palette
```css
/* Light Mode */
--bg-primary: #FFFFFF;
--bg-secondary: #F8F9FA;
--bg-tertiary: #F1F3F5;
--text-primary: #1A1A1A;
--text-secondary: #6B7280;
--text-tertiary: #9CA3AF;
--accent-primary: #6366F1;      /* Indigo - 用于 CTA 按钮 */
--accent-secondary: #8B5CF6;    /* Violet - 渐变辅助色 */
--accent-hover: #4F46E5;
--border: #E5E7EB;
--shadow: rgba(0, 0, 0, 0.04);

/* Dark Mode */
--bg-primary-dark: #0F0F0F;
--bg-secondary-dark: #18181B;
--bg-tertiary-dark: #27272A;
--text-primary-dark: #FAFAFA;
--text-secondary-dark: #A1A1AA;
--text-tertiary-dark: #71717A;
--accent-primary-dark: #818CF8;
--border-dark: #27272A;
```

### Typography
- **Display/Headlines**: `Source Serif 4` (Google Fonts) — 衬线体赋予编辑感
- **Body/UI**: `Geist` 或 `Inter` (但避免直接使用，参考其简洁风格)
- **Chinese Fallback**: `Noto Serif SC` / `Noto Sans SC`
- **Monospace** (用于数据): `JetBrains Mono`

### Spatial System
- Base unit: 4px
- Card padding: 24px
- Section gap: 48px
- Border radius: 12px (cards), 8px (buttons), 24px (large containers)

### Motion Philosophy
- **Entrance**: 渐入 + 轻微上移，stagger 100ms
- **Hover**: 柔和提升 (translateY -2px) + 阴影加深
- **Transitions**: 300ms ease-out (颜色变化), 400ms ease-out (布局)
- **卡片堆叠**: 利用 scale 和 opacity 创造深度感

## 3. Layout & Structure

### Overall Layout
```
┌─────────────────────────────────────────────────────────────┐
│                    Browser Chrome (optional)                 │
├──────────────┬──────────────────────────────────────────────┤
│              │                                               │
│   Sidebar    │              Main Content                     │
│   (240px)    │                                               │
│              │  ┌─────────────────────────────────────────┐  │
│  - Logo      │  │  Header: Group Members                  │  │
│  - Nav       │  │  [Stacked Profile Cards]                │  │
│  - Groups    │  └─────────────────────────────────────────┘  │
│  - User      │                                               │
│              │  ┌─────────────────────────────────────────┐  │
│              │  │  Historical Briefings                   │  │
│              │  │  [3-column Grid of Summary Cards]        │  │
│              │  └─────────────────────────────────────────┘  │
│              │                                               │
└──────────────┴──────────────────────────────────────────────┘
```

### Responsive Strategy
- Desktop (1280px+): Full 3-column grid, sidebar visible
- Tablet (768px-1279px): Sidebar collapsible, 2-column grid
- Mobile (<768px): Single column, bottom nav

## 4. Features & Interactions

### Sidebar Navigation
- **Logo/Brand**: "Curated Daily" with subtle gradient
- **Nav Items**: Control Panel, Discover, My Collection
- **Active State**: Light blue fill (#EFF6FF) with left accent border
- **Group List**: Scrollable list of subscribed Twitter accounts
- **Pro Upgrade Button**: Gradient purple button with sparkle icon
- **User Profile**: Avatar + name at bottom with settings dropdown

### Group Members Section
- **Stacked Card Effect**: Cards overlap by 8px, scale from 1.0 to 0.95
- **Card Content**: Avatar, Name, Handle, Follower count, Bio snippet
- **Hover**: Unstack animation (cards spread apart slightly)
- **Interaction**: Click to view all tweets from this member

### Historical Briefings Section
- **Card Grid**: 3 columns, masonry-style height variation
- **Card Anatomy**:
  - Header: Source icon + name + date
  - Title: AI-generated summary headline (bold serif)
  - Preview: 2-3 bullet points
  - Footer: Tweet count + read time
- **Hover**: Subtle lift + border highlight
- **Click**: Expand to full summary view

### Theme & Language Toggles
- Toggle switches at top of sidebar
- Instant theme switch with smooth color transition
- Language: 中文 / English

## 5. Component Inventory

### SidebarNav
- States: Default, Hover (bg lighten), Active (blue fill + border)
- Transition: 200ms background-color

### MemberCard (Stacked)
- Default: Compact stack visualization
- Hover: Expand stack, show all members clearly
- Active: Highlight selected member

### BriefingCard
- Default: Resting with subtle shadow
- Hover: Lift 4px, shadow deepens, border accent
- Loading: Skeleton with shimmer animation

### ProUpgradeButton
- Default: Gradient background (violet to indigo)
- Hover: Brighten gradient, subtle glow effect
- Active: Scale down slightly (0.98)

### ToggleSwitch
- Off: Gray track, white knob left
- On: Accent color track, white knob right
- Transition: 200ms cubic-bezier for smooth slide

### Avatar
- Sizes: 32px (nav), 48px (member card), 64px (profile)
- Fallback: Initials on gradient background

## 6. Technical Approach

### Stack
- **Framework**: Next.js 15 (App Router)
- **Styling**: CSS Modules + CSS Variables
- **Icons**: Lucide React
- **State**: React hooks (useState, useContext for theme)
- **Animation**: CSS transitions + Framer Motion for complex sequences

### Key Implementation Details
- CSS Variables for theming (instant dark/light switch)
- CSS Grid for briefing card layout
- Intersection Observer for staggered card entrance
- LocalStorage for theme preference persistence

### File Structure
```
frontend/
├── app/
│   ├── layout.tsx          # Root layout with providers
│   ├── page.tsx            # Main dashboard
│   ├── globals.css         # CSS variables + reset
├── components/
│   ├── Sidebar/
│   ├── MemberCard/
│   ├── BriefingCard/
│   ├── ThemeToggle/
│   └── ui/                 # Shared primitives
├── lib/
│   └── api.ts              # API client
└── public/
```
