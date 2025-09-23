<?php

namespace LaravelTests\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;

class Category extends Model
{
    protected $table = 'laravel_categories';
    
    protected $fillable = [
        'name',
        'slug',
        'description',
        'color',
        'metadata_info',
        'is_active',
    ];

    protected $casts = [
        'metadata_info' => 'array',
        'is_active' => 'boolean',
        'created_at' => 'datetime',
        'updated_at' => 'datetime',
    ];

    protected $attributes = [
        'is_active' => true,
        'metadata_info' => '{}',
    ];

    public function posts(): HasMany
    {
        return $this->hasMany(Post::class);
    }

    // Scopes
    public function scopeActive($query)
    {
        return $query->where('is_active', true);
    }

    public function scopeWithSlug($query, $slug)
    {
        return $query->where('slug', $slug);
    }

    // Accessors
    public function getPostCountAttribute()
    {
        return $this->posts()->count();
    }
}
