using System.Linq;
using System.Threading.Tasks;
using Dapper;
using Infrastructure.Data;
using Infrastructure.Repositories;
using Microsoft.Data.Sqlite;
using Xunit;

public class SchemaMigrationTests
{
    [Fact]
    public async Task MigratesLegacySchema()
    {
        var connString = "Data Source=mem_schema.db;Mode=Memory;Cache=Shared";
        using var keepAlive = new SqliteConnection(connString);
        keepAlive.Open();

        var legacyUsers = @"CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL
        );";
        var legacyEntries = @"CREATE TABLE entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL
        );";
        keepAlive.Execute(legacyUsers);
        keepAlive.Execute(legacyEntries);

        var factory = new SqliteConnectionFactory(connString);
        var db = new LoggingDataAccess(factory);
        await db.InitializeAsync();
        var entryRepo = new EntryRepository(db);
        await entryRepo.InitializeAsync();
        var userRepo = new UserRepository(db);
        await userRepo.InitializeAsync();

        using var check = new SqliteConnection(connString);
        var userCols = (await check.QueryAsync("PRAGMA table_info(users);"))
            .Select(r => (string)r.name)
            .ToList();
        var entryCols = (await check.QueryAsync("PRAGMA table_info(entries);"))
            .Select(r => (string)r.name)
            .ToList();

        Assert.Contains("email", userCols);
        Assert.Contains("tags", entryCols);
        Assert.Contains("created_at", entryCols);
    }
}
