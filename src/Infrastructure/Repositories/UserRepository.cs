using Domain.Entities;
using Domain.Interfaces;
using Infrastructure.Data;
using Dapper;
using Microsoft.Data.Sqlite;
using System.Data;
using System.Linq;
using System.Threading;

namespace Infrastructure.Repositories;

public class UserRepository : BaseRepository<User>, IUserRepository
{
    private static readonly SemaphoreSlim _migrationLock = new(1, 1);
    private static bool _schemaEnsured;

    public UserRepository(LoggingDataAccess db) : base(db, "users")
    {
    }

    private async Task EnsureSchemaAsync()
    {
        if (_schemaEnsured) return;
        await _migrationLock.WaitAsync();
        try
        {
            if (_schemaEnsured) return;

            using var connection = _db.CreateConnection();
            await ((SqliteConnection)connection).OpenAsync();
            using var transaction = connection.BeginTransaction();

        var columns = (await connection.QueryAsync("PRAGMA table_info(users);", transaction: transaction)).ToList();
        var hasTable = columns.Any();
        var hasEmail = columns.Any(c => string.Equals((string)c.name, "email", StringComparison.OrdinalIgnoreCase));
        var hasCreatedAt = columns.Any(c => string.Equals((string)c.name, "created_at", StringComparison.OrdinalIgnoreCase));
        var hasHashedPassword = columns.Any(c => string.Equals((string)c.name, "hashed_password", StringComparison.OrdinalIgnoreCase));

            if (!hasTable)
            {
                var create = @"CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            hashed_password TEXT NOT NULL,
            email TEXT NOT NULL,
            created_at TEXT NOT NULL
        );";
                await connection.ExecuteAsync(create, transaction: transaction);
            }
            else if (!hasEmail || !hasCreatedAt || !hasHashedPassword)
            {
                try
                {
                    if (!hasEmail)
                    {
                        await connection.ExecuteAsync("ALTER TABLE users ADD COLUMN email TEXT NOT NULL DEFAULT '';", transaction: transaction);
                    }

                    if (!hasCreatedAt)
                    {
                        await connection.ExecuteAsync("ALTER TABLE users ADD COLUMN created_at TEXT NOT NULL DEFAULT '';", transaction: transaction);
                    }

                    if (!hasHashedPassword)
                    {
                        await connection.ExecuteAsync("ALTER TABLE users ADD COLUMN hashed_password TEXT NOT NULL DEFAULT '';", transaction: transaction);
                    }
                }
                catch (SqliteException ex) when (ex.Message.Contains("duplicate", StringComparison.OrdinalIgnoreCase))
                {
                    // ignore if column already exists
                }
            }

            transaction.Commit();
            _schemaEnsured = true;
        }
        finally
        {
            _migrationLock.Release();
        }
    }

    public async Task InitializeAsync()
    {
        await EnsureSchemaAsync();

        var sql = @"
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            hashed_password TEXT NOT NULL,
            email TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            is_done INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS llm_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            prompt TEXT NOT NULL,
            response TEXT NOT NULL,
            model TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        CREATE VIEW IF NOT EXISTS user_stats AS
            SELECT u.id AS UserId, u.username AS Username,
                COUNT(DISTINCT e.id) AS EntryCount,
                COUNT(DISTINCT t.id) AS TaskCount
            FROM users u
                LEFT JOIN entries e ON e.user_id = u.id
                LEFT JOIN tasks t ON t.user_id = u.id
            GROUP BY u.id;";
        await _db.ExecuteAsync(sql);
    }

    public async Task<UserStats?> GetStatsAsync(int userId)
    {
        var sql = "SELECT UserId, Username, EntryCount, TaskCount FROM user_stats WHERE UserId = @UserId";
        return await _db.QuerySingleOrDefaultAsync<UserStats>(sql, new { UserId = userId });
    }

    public async Task<User?> GetByUsernameAsync(string username)
    {
        var sql = "SELECT * FROM users WHERE username = @Username LIMIT 1";
        return await _db.QuerySingleOrDefaultAsync<User>(sql, new { Username = username });
    }
}
