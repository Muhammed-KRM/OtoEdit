using System.Text.Json;
using Microsoft.Extensions.Logging;
using OtoEdit.Business.Interfaces;
using StackExchange.Redis;

namespace OtoEdit.Business.Infrastructure.Cache;

/// <summary>
/// Redis tabanlı önbellekleme servisi implementasyonu.
/// </summary>
public class RedisCacheService : ICacheService
{
    private readonly IConnectionMultiplexer _redis;
    private readonly ILogger<RedisCacheService> _logger;

    public RedisCacheService(IConnectionMultiplexer redis, ILogger<RedisCacheService> logger)
    {
        _redis = redis;
        _logger = logger;
    }

    public async Task<T?> GetAsync<T>(string key, CancellationToken cancellationToken = default)
    {
        try
        {
            var db = _redis.GetDatabase();
            var val = await db.StringGetAsync(key);
            if (!val.HasValue) return default;

            return JsonSerializer.Deserialize<T>(val.ToString());
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Redis cache okuma hatası: Key={Key}", key);
            return default;
        }
    }

    public async Task SetAsync<T>(string key, T value, TimeSpan? expiry = null, CancellationToken cancellationToken = default)
    {
        try
        {
            var db = _redis.GetDatabase();
            var json = JsonSerializer.Serialize(value);
            if (expiry.HasValue)
            {
                await db.StringSetAsync(key, json, expiry.Value);
            }
            else
            {
                await db.StringSetAsync(key, json);
            }
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Redis cache yazma hatası: Key={Key}", key);
        }
    }

    public async Task RemoveAsync(string key, CancellationToken cancellationToken = default)
    {
        try
        {
            var db = _redis.GetDatabase();
            await db.KeyDeleteAsync(key);
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Redis cache silme hatası: Key={Key}", key);
        }
    }

    public async Task RemoveByPrefixAsync(string prefix, CancellationToken cancellationToken = default)
    {
        try
        {
            var endpoints = _redis.GetEndPoints();
            var db = _redis.GetDatabase();
            foreach (var endpoint in endpoints)
            {
                var server = _redis.GetServer(endpoint);
                var keys = server.Keys(pattern: $"{prefix}*").ToArray();
                if (keys.Length > 0)
                {
                    await db.KeyDeleteAsync(keys);
                }
            }
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Redis cache prefix ile silme hatası: Prefix={Prefix}", prefix);
        }
    }
}
