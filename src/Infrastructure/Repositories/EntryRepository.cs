using Dapper;
using Domain.Entities;
using Domain.Interfaces;
using Infrastructure.Data;
using Infrastructure.QueryBuilders;

namespace Infrastructure.Repositories;

public class EntryRepository : BaseRepository<Entry>, IEntryRepository
{
    public EntryRepository(LoggingDataAccess db) : base(db, "entries")
    {
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
            tags TEXT,
            created_at TEXT NOT NULL,
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
    }


    public async Task<IEnumerable<Entry>> QueryAsync(EntryQueryOptions options)
    {
        var builder = new EntryQueryBuilder(options);
        var (sql, parameters) = builder.Build();
        return await _db.QueryAsync<Entry>(sql, parameters);
    }
}
