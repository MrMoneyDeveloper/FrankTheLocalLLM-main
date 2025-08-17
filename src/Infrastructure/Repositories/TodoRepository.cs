using Domain.Entities;
using Domain.Interfaces;
using Infrastructure.Data;

namespace Infrastructure.Repositories;

public class TodoRepository : BaseRepository<TodoItem>, ITodoRepository
{
    public TodoRepository(LoggingDataAccess db) : base(db, "todos")
    {
    }

    public async Task InitializeAsync()
    {
        var query = @"CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            is_completed INTEGER NOT NULL
        );";
        await _db.ExecuteAsync(query);

        // Migrate legacy column names from early revisions that used
        // PascalCase. Older databases may contain columns named
        // `Title` or `IsCompleted`, which break inserts expecting the
        // lowercase versions. Rename them if they exist so the schema
        // matches the current code.
        var checkOld = "SELECT COUNT(*) FROM pragma_table_info('todos') WHERE name = @Name";
        if (await _db.ExecuteScalarAsync<long>(checkOld, new { Name = "IsCompleted" }) > 0)
        {
            await _db.ExecuteAsync("ALTER TABLE todos RENAME COLUMN IsCompleted TO is_completed;");
        }
        if (await _db.ExecuteScalarAsync<long>(checkOld, new { Name = "Title" }) > 0)
        {
            await _db.ExecuteAsync("ALTER TABLE todos RENAME COLUMN Title TO title;");
        }
    }

}
