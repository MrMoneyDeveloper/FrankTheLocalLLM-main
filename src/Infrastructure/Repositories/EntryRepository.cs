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
            content TEXT NOT NULL,
            tags TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );";
        await _db.ExecuteAsync(sql);

        // Handle databases created before the user_id column existed. In
        // older revisions entries were stored without linking back to the
        // user, so queries against the user_stats view would fail. Ensure the
        // column is present before continuing.
        var check = "SELECT COUNT(*) FROM pragma_table_info('entries') WHERE name = @Name";
        if (await _db.ExecuteScalarAsync<long>(check, new { Name = "user_id" }) == 0)
        {
            // Add the column with a NULL default to avoid errors when existing
            // rows are present. New inserts will supply a valid user id.
            await _db.ExecuteAsync("ALTER TABLE entries ADD COLUMN user_id INTEGER;");
        }
    }


    public async Task<IEnumerable<Entry>> QueryAsync(EntryQueryOptions options)
    {
        var builder = new EntryQueryBuilder(options);
        var (sql, parameters) = builder.Build();
        return await _db.QueryAsync<Entry>(sql, parameters);
    }
}
