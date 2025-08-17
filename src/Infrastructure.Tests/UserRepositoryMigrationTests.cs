using System;
using System.Linq;
using System.Threading.Tasks;
using Dapper;
using Infrastructure.Data;
using Infrastructure.Repositories;
using Microsoft.Data.Sqlite;
using Xunit;
using Domain.Entities;

public class UserRepositoryMigrationTests
{
    [Fact]
    public async Task AddsEmailColumnToLegacySchema()
    {
        var connString = "Data Source=mem_users.db;Mode=Memory;Cache=Shared";
        using var keepAlive = new SqliteConnection(connString);
        keepAlive.Open();

        var legacy = @"CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL
        );";
        keepAlive.Execute(legacy);

        var factory = new SqliteConnectionFactory(connString);
        var db = new LoggingDataAccess(factory);
        await db.InitializeAsync();
        var repo = new UserRepository(db);
        await repo.InitializeAsync();

        using var check = new SqliteConnection(connString);
        var cols = (await check.QueryAsync("PRAGMA table_info(users);"))
            .Select(r => (string)r.name)
            .ToList();
        Assert.Contains("email", cols);

        var id = await repo.AddAsync(new User { Username = "bob", Email = "b@example.com", CreatedAt = DateTime.UtcNow });
        var saved = await repo.GetByIdAsync(id);
        Assert.NotNull(saved);
        Assert.Equal("b@example.com", saved!.Email);
    }
}
