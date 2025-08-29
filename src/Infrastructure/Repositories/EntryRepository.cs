using System;
using Dapper;
using Domain.Entities;
using Domain.Interfaces;
using Infrastructure.Data;
using Infrastructure.QueryBuilders;
using Microsoft.Data.Sqlite;
using Microsoft.Extensions.Logging;

namespace Infrastructure.Repositories;

public class EntryRepository : BaseRepository<Entry>, IEntryRepository
{
    private readonly ILogger<EntryRepository> _logger;

    public EntryRepository(LoggingDataAccess db, ILogger<EntryRepository> logger) : base(db, "entries")
    {
        _logger = logger;
    }

    public async Task InitializeAsync()
    {
        var sql = @"CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL DEFAULT '',
            ""group"" TEXT NOT NULL DEFAULT '',
            content TEXT NOT NULL,
            summary TEXT NOT NULL DEFAULT '',
            is_summarised INTEGER NOT NULL DEFAULT 0,
            tags TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ')),
            FOREIGN KEY(user_id) REFERENCES users(id)
        );";
        await _db.ExecuteAsync(sql);

        var check = "SELECT COUNT(*) FROM pragma_table_info('entries') WHERE name = @Name";

        if (await _db.ExecuteScalarAsync<long>(check, new { Name = "user_id" }) == 0)
        {
            await _db.ExecuteAsync("ALTER TABLE entries ADD COLUMN user_id INTEGER;");
        }
        if (await _db.ExecuteScalarAsync<long>(check, new { Name = "title" }) == 0)
        {
            await _db.ExecuteAsync("ALTER TABLE entries ADD COLUMN title TEXT NOT NULL DEFAULT '';");
        }
        if (await _db.ExecuteScalarAsync<long>(check, new { Name = "group" }) == 0)
        {
            await _db.ExecuteAsync("ALTER TABLE entries ADD COLUMN \"group\" TEXT NOT NULL DEFAULT '';");
        }
        if (await _db.ExecuteScalarAsync<long>(check, new { Name = "summary" }) == 0)
        {
            await _db.ExecuteAsync("ALTER TABLE entries ADD COLUMN summary TEXT NOT NULL DEFAULT '';");
        }
        if (await _db.ExecuteScalarAsync<long>(check, new { Name = "is_summarised" }) == 0)
        {
            await _db.ExecuteAsync("ALTER TABLE entries ADD COLUMN is_summarised INTEGER NOT NULL DEFAULT 0;");
        }
        if (await _db.ExecuteScalarAsync<long>(check, new { Name = "tags" }) == 0)
        {
            await _db.ExecuteAsync("ALTER TABLE entries ADD COLUMN tags TEXT NOT NULL DEFAULT '';");
        }
        if (await _db.ExecuteScalarAsync<long>(check, new { Name = "created_at" }) == 0)
        {
            await _db.ExecuteAsync("ALTER TABLE entries ADD COLUMN created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ'));");
        }

        if (await _db.ExecuteScalarAsync<int>("SELECT COUNT(*) FROM entries") == 0)
        {
            try
            {
                await _db.ExecuteAsync(
                    @"INSERT INTO entries (user_id, title, [group], content, summary, is_summarised, tags, created_at)
                      VALUES (@UserId, @Title, @Group, @Content, @Summary, @IsSummarised, @Tags, @CreatedAt)",
                    new
                    {
                        UserId = 1,
                        Title = "Welcome",
                        Group = "General",
                        Content = "This is your first entry.",
                        Summary = string.Empty,
                        IsSummarised = false,
                        Tags = string.Empty,
                        CreatedAt = DateTime.UtcNow
                    });
            }
            catch (SqliteException ex)
            {
                _logger.LogError(ex, "Failed to insert default entry");
            }
        }
    }

    public override async Task<int> AddAsync(Entry entity)
    {
        // Normalize at the boundary to avoid NOT NULL violations
        NormalizeEntity(entity);
        try
        {
            return await base.AddAsync(entity);
        }
        catch (SqliteException ex) when (IsNotNullConstraint(ex))
        {
            // Last-resort retry: force a safe title and try once
            var originalTitle = entity.Title;
            entity.Title = string.IsNullOrWhiteSpace(originalTitle) ? "Untitled" : originalTitle;
            try
            {
                return await base.AddAsync(entity);
            }
            catch (SqliteException retryEx)
            {
                _logger.LogError(retryEx, "Retry insert failed for entry after title fallback.");
                throw new InvalidOperationException("Failed to save entry after retry.", retryEx);
            }
        }
        catch (SqliteException ex)
        {
            _logger.LogError(ex, "Database error while inserting entry.");
            throw new InvalidOperationException("Failed to save entry.", ex);
        }
    }

    private static void NormalizeEntity(Entry e)
    {
        // Ensure all NOT NULL columns have non-null values
        e.Title = SafeTitle(e.Title, e.Content);
        e.Group = e.Group ?? string.Empty;
        e.Content = e.Content ?? string.Empty;
        e.Summary = e.Summary ?? string.Empty;
        e.Tags = e.Tags ?? string.Empty;
        if (e.CreatedAt == default)
        {
            e.CreatedAt = DateTime.UtcNow;
        }
    }

    private static string SafeTitle(string? title, string? content)
    {
        if (!string.IsNullOrWhiteSpace(title)) return title!;
        // Derive a lightweight title from the first non-empty content line
        var candidate = (content ?? string.Empty)
            .Split(new[] { '\n', '\r' }, StringSplitOptions.RemoveEmptyEntries)
            .Select(s => s.Trim())
            .FirstOrDefault(s => !string.IsNullOrWhiteSpace(s));
        if (string.IsNullOrWhiteSpace(candidate)) return "Untitled";
        // Truncate to a sensible length for titles
        return candidate!.Length <= 120 ? candidate : candidate.Substring(0, 120);
    }

    private static bool IsNotNullConstraint(SqliteException ex)
        => ex.SqliteErrorCode == 19 /* SQLITE_CONSTRAINT */
           && ex.Message.Contains("NOT NULL constraint failed", StringComparison.OrdinalIgnoreCase);

    public async Task<IEnumerable<Entry>> QueryAsync(EntryQueryOptions options)
    {
        var builder = new EntryQueryBuilder(options);
        var (sql, parameters) = builder.Build();
        return await _db.QueryAsync<Entry>(sql, parameters);
    }
}
