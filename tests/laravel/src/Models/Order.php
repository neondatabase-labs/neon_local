<?php

namespace LaravelTests\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class Order extends Model
{
    protected $table = 'laravel_orders';
    
    protected $fillable = [
        'user_id',
        'order_number',
        'status',
        'total_amount',
        'items_data',
        'shipping_address',
        'metadata_info',
    ];

    protected $casts = [
        'total_amount' => 'decimal:2',
        'items_data' => 'array',
        'shipping_address' => 'array',
        'metadata_info' => 'array',
        'created_at' => 'datetime',
        'updated_at' => 'datetime',
    ];

    protected $attributes = [
        'status' => 'pending',
        'total_amount' => 0.00,
        'items_data' => '[]',
        'shipping_address' => '{}',
        'metadata_info' => '{}',
    ];

    public function user(): BelongsTo
    {
        return $this->belongsTo(User::class);
    }

    // Scopes
    public function scopeWithStatus($query, $status)
    {
        return $query->where('status', $status);
    }

    public function scopeForUser($query, $userId)
    {
        return $query->where('user_id', $userId);
    }

    public function scopeCompleted($query)
    {
        return $query->where('status', 'completed');
    }

    // Accessors
    public function getFormattedTotalAttribute()
    {
        return '$' . number_format($this->total_amount, 2);
    }

    public function getItemCountAttribute()
    {
        return count($this->items_data);
    }
}
