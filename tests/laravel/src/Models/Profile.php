<?php

namespace LaravelTests\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class Profile extends Model
{
    protected $table = 'laravel_profiles';
    
    protected $fillable = [
        'user_id',
        'bio',
        'avatar_url',
        'social_links',
        'preferences',
        'settings',
    ];

    protected $casts = [
        'social_links' => 'array',
        'preferences' => 'array',
        'settings' => 'array',
        'created_at' => 'datetime',
        'updated_at' => 'datetime',
    ];

    protected $attributes = [
        'social_links' => '{}',
        'preferences' => '{}',
        'settings' => '{}',
    ];

    public function user(): BelongsTo
    {
        return $this->belongsTo(User::class);
    }
}
