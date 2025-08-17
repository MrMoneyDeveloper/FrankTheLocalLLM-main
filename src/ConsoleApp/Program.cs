using Domain.Entities;
using Domain.Interfaces;
using Infrastructure.Data;
using Infrastructure.Repositories;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;

var configuration = new ConfigurationBuilder()
    .AddJsonFile("appsettings.json", optional: true)
    .AddEnvironmentVariables()
    .Build();

var services = new ServiceCollection();

var connectionString = configuration.GetConnectionString("Default") ?? "Data Source=app.db";
services.AddSingleton(new SqliteConnectionFactory(connectionString));
services.AddSingleton<LoggingDataAccess>();
services.AddScoped<ITodoRepository, TodoRepository>();
services.AddScoped<IUserRepository, UserRepository>();
services.AddScoped<IEntryRepository, EntryRepository>();

var provider = services.BuildServiceProvider();

var db = provider.GetRequiredService<LoggingDataAccess>();
await db.InitializeAsync();

var todoRepo = provider.GetRequiredService<ITodoRepository>();
await todoRepo.InitializeAsync();

// Initialize the entry repository before the user repository so
// the `entries` table has the required columns when the
// `user_stats` view is created. Older databases may lack the
// `user_id` column, which would cause queries against the view to
// fail with a "no such column" error.
var entryRepo = provider.GetRequiredService<IEntryRepository>();
await entryRepo.InitializeAsync();

var todoId = await todoRepo.AddAsync(new TodoItem { Title = "Learn Dapper", IsCompleted = false });
Console.WriteLine($"Inserted Todo with Id {todoId}");

var items = await todoRepo.GetAllAsync();
foreach (var item in items)
{
    Console.WriteLine($"{item.Id}: {item.Title} - {(item.IsCompleted ? "Done" : "Pending")}");
}

var userRepo = provider.GetRequiredService<IUserRepository>();
await userRepo.InitializeAsync();
var existing = await userRepo.GetByUsernameAsync("alice");
int userId;
if (existing != null)
{
    userId = existing.Id;
    Console.WriteLine($"Using existing user with Id {userId}");
}
else
{
    userId = await userRepo.AddAsync(new User
    {
        Username = "alice",
        HashedPassword = "dummy",
        Email = "alice@example.com",
        CreatedAt = DateTime.UtcNow
    });
    Console.WriteLine($"Inserted User with Id {userId}");
}
var stats = await userRepo.GetStatsAsync(userId);
if (stats != null)
{
    Console.WriteLine($"Stats for {stats.Username}: Entries={stats.EntryCount}, Tasks={stats.TaskCount}");
}

// `entryRepo` was initialized earlier. Use it now to insert and query entries.
var entryId = await entryRepo.AddAsync(new Entry { UserId = userId, Content = "First post", Tags = "intro,example", CreatedAt = DateTime.UtcNow });
Console.WriteLine($"Inserted Entry with Id {entryId}");

var options = new EntryQueryOptions { Tags = new[] { "intro" } };
var entries = await entryRepo.QueryAsync(options);
foreach (var e in entries)
{
    Console.WriteLine($"Entry {e.Id}: {e.Content} [{e.Tags}]");
}
