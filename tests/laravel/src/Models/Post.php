<?php

namespace LaravelTests\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Illuminate\Database\Eloquent\Relations\BelongsToMany;

class Post extends Model
{
    protected $table = 'laravel_posts';
    
    protected $fillable = [
        'title',
        'slug',
        'content',
        'author_id',
        'category_id',
        'published',
        'tags',
        'view_count',
        'rating',
        'metadata',
    ];

    protected $casts = [
        'published' => 'boolean',
        'tags' => 'array',
        'view_count' => 'integer',
        'rating' => 'decimal:2',
        'metadata' => 'array',
        'created_at' => 'datetime',
        'updated_at' => 'datetime',
    ];

    protected $attributes = [
        'published' => false,
        'view_count' => 0,
        'rating' => 0.0,
        'tags' => '[]',
        'metadata' => '{}',
    ];

    public function author(): BelongsTo
    {
        return $this->belongsTo(User::class, 'author_id');
    }

    public function category(): BelongsTo
    {
        return $this->belongsTo(Category::class);
    }

    public function comments(): HasMany
    {
        return $this->hasMany(Comment::class);
    }

    public function postTags(): BelongsToMany
    {
        return $this->belongsToMany(Tag::class, 'laravel_post_tags')
                    ->withTimestamps();
    }

    // Scopes
    public function scopePublished($query)
    {
        return $query->where('published', true);
    }

    public function scopeByAuthor($query, $authorId)
    {
        return $query->where('author_id', $authorId);
    }

    public function scopeInCategory($query, $categoryId)
    {
        return $query->where('category_id', $categoryId);
    }

    public function scopePopular($query, $minViews = 100)
    {
        return $query->where('view_count', '>=', $minViews);
    }

    public function scopeWithTag($query, $tag)
    {
        return $query->whereJsonContains('tags', $tag);
    }

    // Accessors
    public function getExcerptAttribute()
    {
        return substr($this->content, 0, 150) . '...';
    }

    public function getReadTimeAttribute()
    {
        $words = str_word_count($this->content);
        return ceil($words / 200); // Assuming 200 words per minute
    }
}
