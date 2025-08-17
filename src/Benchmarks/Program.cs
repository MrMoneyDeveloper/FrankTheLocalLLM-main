using BenchmarkDotNet.Attributes;
using BenchmarkDotNet.Running;
using Infrastructure.Data;
using Microsoft.Data.Sqlite;

BenchmarkRunner.Run<DapperBenchmarks>();

public class DapperBenchmarks
{
    private LoggingDataAccess _db = null!;

    [GlobalSetup]
    public void Setup()
    {
        var factory = new SqliteConnectionFactory("Data Source=:memory:");
        _db = new LoggingDataAccess(factory);
        _db.InitializeAsync().GetAwaiter().GetResult();
    }

    [Benchmark]
    public int ExecuteScalar()
    {
        return _db.ExecuteScalarAsync<int>("SELECT 1").GetAwaiter().GetResult();
    }
}
