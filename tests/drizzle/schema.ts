// Comprehensive Drizzle ORM schema for testing
// This schema includes various data types, relationships, and advanced features

import {
  pgTable,
  serial,
  varchar,
  text,
  integer,
  boolean,
  decimal,
  timestamp,
  date,
  time,
  json,
  jsonb,
  uuid,
  real,
  doublePrecision,
  smallint,
  bigint,
  char,
  index,
  unique,
  primaryKey,
  foreignKey,
  check
} from 'drizzle-orm/pg-core';
import { relations } from 'drizzle-orm';

// Users table with comprehensive data types
export const users = pgTable('drizzle_users', {
  id: serial('id').primaryKey(),
  uuid: uuid('uuid').defaultRandom().notNull(),
  email: varchar('email', { length: 255 }).unique().notNull(),
  username: varchar('username', { length: 50 }).unique(),
  firstName: varchar('first_name', { length: 100 }),
  lastName: varchar('last_name', { length: 100 }),
  fullName: varchar('full_name', { length: 200 }),
  age: integer('age'),
  isActive: boolean('is_active').default(true).notNull(),
  isVerified: boolean('is_verified').default(false),
  salary: decimal('salary', { precision: 12, scale: 2 }),
  rating: real('rating').default(0),
  score: doublePrecision('score').default(0),
  bio: text('bio'),
  metadata: json('metadata').$type<{
    preferences: Record<string, any>;
    settings: Record<string, any>;
    tags: string[];
  }>(),
  profileData: jsonb('profile_data').$type<{
    social: { platform: string; handle: string }[];
    skills: string[];
    experience: number;
  }>(),
  loginCount: smallint('login_count').default(0),
  totalPoints: bigint('total_points', { mode: 'number' }).default(0),
  status: char('status', { length: 1 }).default('A'), // A=Active, I=Inactive, P=Pending
  createdAt: timestamp('created_at').defaultNow().notNull(),
  updatedAt: timestamp('updated_at').defaultNow().notNull(),
  lastLoginAt: timestamp('last_login_at'),
  birthDate: date('birth_date'),
  preferredTime: time('preferred_time')
}, (table) => ({
  emailIdx: index('drizzle_users_email_idx').on(table.email),
  activeUsersIdx: index('drizzle_users_active_idx').on(table.isActive),
  createdAtIdx: index('drizzle_users_created_at_idx').on(table.createdAt),
  ageCheck: check('age_check', sql`age >= 0 AND age <= 150`),
  salaryCheck: check('salary_check', sql`salary >= 0`)
}));

// Categories table with self-referential relationships
export const categories = pgTable('drizzle_categories', {
  id: serial('id').primaryKey(),
  name: varchar('name', { length: 100 }).unique().notNull(),
  slug: varchar('slug', { length: 100 }).unique().notNull(),
  description: text('description'),
  color: char('color', { length: 7 }).default('#000000'), // Hex color
  isActive: boolean('is_active').default(true),
  sortOrder: integer('sort_order').default(0),
  parentId: integer('parent_id'),
  metadata: jsonb('metadata').$type<{
    icon?: string;
    featured?: boolean;
    seoTitle?: string;
    seoDescription?: string;
  }>(),
  createdAt: timestamp('created_at').defaultNow().notNull(),
  updatedAt: timestamp('updated_at').defaultNow().notNull()
}, (table) => ({
  nameIdx: index('drizzle_categories_name_idx').on(table.name),
  parentIdx: index('drizzle_categories_parent_idx').on(table.parentId),
  activeIdx: index('drizzle_categories_active_idx').on(table.isActive),
  parentFk: foreignKey({
    columns: [table.parentId],
    foreignColumns: [table.id],
    name: 'drizzle_categories_parent_fk'
  })
}));

// Posts table with relationships
export const posts = pgTable('drizzle_posts', {
  id: serial('id').primaryKey(),
  uuid: uuid('uuid').defaultRandom().notNull(),
  title: varchar('title', { length: 255 }).notNull(),
  slug: varchar('slug', { length: 255 }).unique().notNull(),
  excerpt: varchar('excerpt', { length: 500 }),
  content: text('content'),
  status: varchar('status', { length: 20 }).default('draft'), // draft, published, archived
  isPublished: boolean('is_published').default(false),
  isFeatured: boolean('is_featured').default(false),
  publishedAt: timestamp('published_at'),
  viewCount: integer('view_count').default(0),
  likeCount: integer('like_count').default(0),
  commentCount: integer('comment_count').default(0),
  readingTime: smallint('reading_time'), // minutes
  authorId: integer('author_id').notNull(),
  categoryId: integer('category_id'),
  metadata: jsonb('metadata').$type<{
    seo?: { title: string; description: string; keywords: string[] };
    social?: { image: string; title: string; description: string };
    custom?: Record<string, any>;
  }>(),
  createdAt: timestamp('created_at').defaultNow().notNull(),
  updatedAt: timestamp('updated_at').defaultNow().notNull()
}, (table) => ({
  titleIdx: index('drizzle_posts_title_idx').on(table.title),
  slugIdx: unique('drizzle_posts_slug_unique').on(table.slug),
  authorIdx: index('drizzle_posts_author_idx').on(table.authorId),
  categoryIdx: index('drizzle_posts_category_idx').on(table.categoryId),
  publishedIdx: index('drizzle_posts_published_idx').on(table.isPublished),
  statusIdx: index('drizzle_posts_status_idx').on(table.status),
  authorFk: foreignKey({
    columns: [table.authorId],
    foreignColumns: [users.id],
    name: 'drizzle_posts_author_fk'
  }),
  categoryFk: foreignKey({
    columns: [table.categoryId],
    foreignColumns: [categories.id],
    name: 'drizzle_posts_category_fk'
  })
}));

// Comments table with nested relationships
export const comments = pgTable('drizzle_comments', {
  id: serial('id').primaryKey(),
  content: text('content').notNull(),
  authorId: integer('author_id').notNull(),
  postId: integer('post_id').notNull(),
  parentId: integer('parent_id'),
  isApproved: boolean('is_approved').default(false),
  likeCount: integer('like_count').default(0),
  metadata: json('metadata').$type<{
    ipAddress?: string;
    userAgent?: string;
    edited?: boolean;
    editedAt?: string;
  }>(),
  createdAt: timestamp('created_at').defaultNow().notNull(),
  updatedAt: timestamp('updated_at').defaultNow().notNull()
}, (table) => ({
  authorIdx: index('drizzle_comments_author_idx').on(table.authorId),
  postIdx: index('drizzle_comments_post_idx').on(table.postId),
  parentIdx: index('drizzle_comments_parent_idx').on(table.parentId),
  approvedIdx: index('drizzle_comments_approved_idx').on(table.isApproved),
  authorFk: foreignKey({
    columns: [table.authorId],
    foreignColumns: [users.id],
    name: 'drizzle_comments_author_fk'
  }),
  postFk: foreignKey({
    columns: [table.postId],
    foreignColumns: [posts.id],
    name: 'drizzle_comments_post_fk'
  }),
  parentFk: foreignKey({
    columns: [table.parentId],
    foreignColumns: [table.id],
    name: 'drizzle_comments_parent_fk'
  })
}));

// Tags table
export const tags = pgTable('drizzle_tags', {
  id: serial('id').primaryKey(),
  name: varchar('name', { length: 50 }).unique().notNull(),
  slug: varchar('slug', { length: 50 }).unique().notNull(),
  description: text('description'),
  color: char('color', { length: 7 }).default('#gray'),
  usageCount: integer('usage_count').default(0),
  isActive: boolean('is_active').default(true),
  metadata: json('metadata').$type<{
    featured?: boolean;
    category?: string;
  }>(),
  createdAt: timestamp('created_at').defaultNow().notNull()
}, (table) => ({
  nameIdx: unique('drizzle_tags_name_unique').on(table.name),
  activeIdx: index('drizzle_tags_active_idx').on(table.isActive),
  usageIdx: index('drizzle_tags_usage_idx').on(table.usageCount)
}));

// Many-to-many relationship table for posts and tags
export const postTags = pgTable('drizzle_post_tags', {
  postId: integer('post_id').notNull(),
  tagId: integer('tag_id').notNull(),
  createdAt: timestamp('created_at').defaultNow().notNull()
}, (table) => ({
  pk: primaryKey({ columns: [table.postId, table.tagId] }),
  postIdx: index('drizzle_post_tags_post_idx').on(table.postId),
  tagIdx: index('drizzle_post_tags_tag_idx').on(table.tagId),
  postFk: foreignKey({
    columns: [table.postId],
    foreignColumns: [posts.id],
    name: 'drizzle_post_tags_post_fk'
  }),
  tagFk: foreignKey({
    columns: [table.tagId],
    foreignColumns: [tags.id],
    name: 'drizzle_post_tags_tag_fk'
  })
}));

// User profiles table (one-to-one relationship)
export const userProfiles = pgTable('drizzle_user_profiles', {
  id: serial('id').primaryKey(),
  userId: integer('user_id').unique().notNull(),
  displayName: varchar('display_name', { length: 100 }),
  bio: text('bio'),
  website: varchar('website', { length: 255 }),
  location: varchar('location', { length: 100 }),
  timezone: varchar('timezone', { length: 50 }),
  language: varchar('language', { length: 10 }).default('en'),
  theme: varchar('theme', { length: 20 }).default('light'),
  avatar: varchar('avatar', { length: 500 }),
  coverImage: varchar('cover_image', { length: 500 }),
  socialLinks: jsonb('social_links').$type<{
    twitter?: string;
    linkedin?: string;
    github?: string;
    website?: string;
  }>(),
  preferences: jsonb('preferences').$type<{
    emailNotifications: boolean;
    pushNotifications: boolean;
    privacy: {
      profileVisibility: 'public' | 'private' | 'friends';
      showEmail: boolean;
      showLocation: boolean;
    };
  }>(),
  stats: json('stats').$type<{
    postsCount: number;
    commentsCount: number;
    likesReceived: number;
    followersCount: number;
    followingCount: number;
  }>(),
  createdAt: timestamp('created_at').defaultNow().notNull(),
  updatedAt: timestamp('updated_at').defaultNow().notNull()
}, (table) => ({
  userIdx: unique('drizzle_user_profiles_user_unique').on(table.userId),
  displayNameIdx: index('drizzle_user_profiles_display_name_idx').on(table.displayName),
  userFk: foreignKey({
    columns: [table.userId],
    foreignColumns: [users.id],
    name: 'drizzle_user_profiles_user_fk'
  })
}));

// Analytics/Events table for testing aggregations
export const analytics = pgTable('drizzle_analytics', {
  id: serial('id').primaryKey(),
  eventType: varchar('event_type', { length: 50 }).notNull(),
  entityType: varchar('entity_type', { length: 50 }), // user, post, comment, etc.
  entityId: integer('entity_id'),
  userId: integer('user_id'),
  sessionId: varchar('session_id', { length: 100 }),
  ipAddress: varchar('ip_address', { length: 45 }),
  userAgent: text('user_agent'),
  referrer: varchar('referrer', { length: 500 }),
  metadata: jsonb('metadata').$type<{
    duration?: number;
    value?: number;
    properties?: Record<string, any>;
  }>(),
  timestamp: timestamp('timestamp').defaultNow().notNull()
}, (table) => ({
  eventTypeIdx: index('drizzle_analytics_event_type_idx').on(table.eventType),
  entityIdx: index('drizzle_analytics_entity_idx').on(table.entityType, table.entityId),
  userIdx: index('drizzle_analytics_user_idx').on(table.userId),
  timestampIdx: index('drizzle_analytics_timestamp_idx').on(table.timestamp),
  sessionIdx: index('drizzle_analytics_session_idx').on(table.sessionId)
}));

// Settings table for testing JSON operations
export const settings = pgTable('drizzle_settings', {
  id: serial('id').primaryKey(),
  key: varchar('key', { length: 100 }).unique().notNull(),
  value: jsonb('value').notNull(),
  category: varchar('category', { length: 50 }).default('general'),
  isPublic: boolean('is_public').default(false),
  isSystem: boolean('is_system').default(false),
  description: text('description'),
  validationSchema: json('validation_schema').$type<{
    type: string;
    required?: boolean;
    properties?: Record<string, any>;
  }>(),
  createdAt: timestamp('created_at').defaultNow().notNull(),
  updatedAt: timestamp('updated_at').defaultNow().notNull()
}, (table) => ({
  keyIdx: unique('drizzle_settings_key_unique').on(table.key),
  categoryIdx: index('drizzle_settings_category_idx').on(table.category),
  publicIdx: index('drizzle_settings_public_idx').on(table.isPublic)
}));

// File uploads table for testing binary data
export const files = pgTable('drizzle_files', {
  id: serial('id').primaryKey(),
  uuid: uuid('uuid').defaultRandom().notNull(),
  filename: varchar('filename', { length: 255 }).notNull(),
  originalName: varchar('original_name', { length: 255 }).notNull(),
  mimeType: varchar('mime_type', { length: 100 }).notNull(),
  fileSize: bigint('file_size', { mode: 'number' }).notNull(),
  width: integer('width'),
  height: integer('height'),
  duration: integer('duration'), // for video/audio files
  path: varchar('path', { length: 500 }).notNull(),
  url: varchar('url', { length: 500 }),
  thumbnailPath: varchar('thumbnail_path', { length: 500 }),
  thumbnailUrl: varchar('thumbnail_url', { length: 500 }),
  uploadedBy: integer('uploaded_by'),
  isPublic: boolean('is_public').default(false),
  metadata: jsonb('metadata').$type<{
    exif?: Record<string, any>;
    processing?: {
      status: 'pending' | 'processing' | 'completed' | 'failed';
      progress?: number;
      error?: string;
    };
    variants?: {
      name: string;
      path: string;
      url: string;
      width?: number;
      height?: number;
      fileSize: number;
    }[];
  }>(),
  createdAt: timestamp('created_at').defaultNow().notNull(),
  updatedAt: timestamp('updated_at').defaultNow().notNull()
}, (table) => ({
  uuidIdx: unique('drizzle_files_uuid_unique').on(table.uuid),
  filenameIdx: index('drizzle_files_filename_idx').on(table.filename),
  mimeTypeIdx: index('drizzle_files_mime_type_idx').on(table.mimeType),
  uploaderIdx: index('drizzle_files_uploader_idx').on(table.uploadedBy),
  publicIdx: index('drizzle_files_public_idx').on(table.isPublic),
  uploaderFk: foreignKey({
    columns: [table.uploadedBy],
    foreignColumns: [users.id],
    name: 'drizzle_files_uploader_fk'
  })
}));

// Define relationships using Drizzle relations
export const usersRelations = relations(users, ({ one, many }) => ({
  profile: one(userProfiles, {
    fields: [users.id],
    references: [userProfiles.userId]
  }),
  posts: many(posts),
  comments: many(comments),
  uploadedFiles: many(files)
}));

export const userProfilesRelations = relations(userProfiles, ({ one }) => ({
  user: one(users, {
    fields: [userProfiles.userId],
    references: [users.id]
  })
}));

export const categoriesRelations = relations(categories, ({ one, many }) => ({
  parent: one(categories, {
    fields: [categories.parentId],
    references: [categories.id]
  }),
  children: many(categories),
  posts: many(posts)
}));

export const postsRelations = relations(posts, ({ one, many }) => ({
  author: one(users, {
    fields: [posts.authorId],
    references: [users.id]
  }),
  category: one(categories, {
    fields: [posts.categoryId],
    references: [categories.id]
  }),
  comments: many(comments),
  tags: many(postTags)
}));

export const commentsRelations = relations(comments, ({ one, many }) => ({
  author: one(users, {
    fields: [comments.authorId],
    references: [users.id]
  }),
  post: one(posts, {
    fields: [comments.postId],
    references: [posts.id]
  }),
  parent: one(comments, {
    fields: [comments.parentId],
    references: [comments.id]
  }),
  children: many(comments)
}));

export const tagsRelations = relations(tags, ({ many }) => ({
  posts: many(postTags)
}));

export const postTagsRelations = relations(postTags, ({ one }) => ({
  post: one(posts, {
    fields: [postTags.postId],
    references: [posts.id]
  }),
  tag: one(tags, {
    fields: [postTags.tagId],
    references: [tags.id]
  })
}));

export const filesRelations = relations(files, ({ one }) => ({
  uploader: one(users, {
    fields: [files.uploadedBy],
    references: [users.id]
  })
}));

// Export schema for use in tests
export const schema = {
  users,
  userProfiles,
  categories,
  posts,
  comments,
  tags,
  postTags,
  analytics,
  settings,
  files,
  // Relations
  usersRelations,
  userProfilesRelations,
  categoriesRelations,
  postsRelations,
  commentsRelations,
  tagsRelations,
  postTagsRelations,
  filesRelations
};

// Import sql for raw queries (needed for check constraints)
import { sql } from 'drizzle-orm';
