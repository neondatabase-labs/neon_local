<?php

namespace LaravelTests\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsToMany;

class Role extends Model
{
    protected $table = 'laravel_roles';
    
    protected $fillable = [
        'name',
        'slug',
        'description',
        'permissions',
        'is_active',
    ];

    protected $casts = [
        'permissions' => 'array',
        'is_active' => 'boolean',
        'created_at' => 'datetime',
        'updated_at' => 'datetime',
    ];

    protected $attributes = [
        'is_active' => true,
        'permissions' => '[]',
    ];

    public function users(): BelongsToMany
    {
        return $this->belongsToMany(User::class, 'laravel_user_roles')
                    ->withPivot(['assigned_at', 'is_active'])
                    ->withTimestamps();
    }

    // Scopes
    public function scopeActive($query)
    {
        return $query->where('is_active', true);
    }

    public function scopeWithPermission($query, $permission)
    {
        return $query->whereJsonContains('permissions', $permission);
    }
}
