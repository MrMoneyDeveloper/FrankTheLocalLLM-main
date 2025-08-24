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
    }

    public override async Task<int> AddAsync(Entry entity)
    {
        try
        {
            return await base.AddAsync(entity);
        }
        catch (SqliteException ex)
        {
            _logger.LogError(ex, "Database error while inserting entry.");
            throw new InvalidOperationException("Failed to save entry.", ex);
        }
    }

    public async Task<IEnumerable<Entry>> QueryAsync(EntryQueryOptions options)
    {
        var builder = new EntryQueryBuilder(options);
        var (sql, parameters) = builder.Build();
        return await _db.QueryAsync<Entry>(sql, parameters);
    }
}
