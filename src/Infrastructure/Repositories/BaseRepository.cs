using System.Text;
using System.Linq;
using Dapper;
using Domain.Entities;
using Infrastructure.Data;

namespace Infrastructure.Repositories;

public abstract class BaseRepository<T> where T : BaseEntity
{
    protected readonly LoggingDataAccess _db;
    private readonly string _insertSql;
    private readonly string _updateSql;
    private readonly string _selectAllSql;
    private readonly string _selectByIdSql;
    private readonly string _deleteSql;

    static BaseRepository()
    {
        DefaultTypeMap.MatchNamesWithUnderscores = true;
        SqlMapper.AddTypeHandler(new BoolIntHandler());
    }

    protected BaseRepository(LoggingDataAccess db, string tableName)
    {
        _db = db;
        _selectAllSql = $"SELECT * FROM {tableName}";
        _selectByIdSql = $"SELECT * FROM {tableName} WHERE id = @Id";
        _deleteSql = $"DELETE FROM {tableName} WHERE id = @Id";

        var props = typeof(T).GetProperties()
            .Where(p => p.Name != nameof(BaseEntity.Id))
            .ToArray();
        var columns = string.Join(", ", props.Select(p => ToSnakeCase(p.Name)));
        var parameters = string.Join(", ", props.Select(p => $"@{p.Name}"));
        _insertSql = $"INSERT INTO {tableName} ({columns}) VALUES ({parameters}); SELECT last_insert_rowid();";
        var sets = string.Join(", ", props.Select(p => $"{ToSnakeCase(p.Name)} = @{p.Name}"));
        _updateSql = $"UPDATE {tableName} SET {sets} WHERE id = @Id";
    }

    private static string ToSnakeCase(string name)
    {
        if (string.IsNullOrEmpty(name)) return name;
        var sb = new StringBuilder();
        for (int i = 0; i < name.Length; i++)
        {
            var c = name[i];
            if (char.IsUpper(c) && i > 0) sb.Append('_');
            sb.Append(char.ToLowerInvariant(c));
        }
        return sb.ToString();
    }

    public virtual async Task<int> AddAsync(T entity)
    {
        var id = await _db.ExecuteScalarAsync<long>(_insertSql, entity);
        return (int)id;
    }

    public virtual async Task<IEnumerable<T>> GetAllAsync()
        => await _db.QueryAsync<T>(_selectAllSql);

    public virtual async Task<T?> GetByIdAsync(int id)
        => await _db.QuerySingleOrDefaultAsync<T>(_selectByIdSql, new { Id = id });

    public virtual async Task UpdateAsync(T entity)
        => await _db.ExecuteAsync(_updateSql, entity);

    public virtual async Task DeleteAsync(int id)
        => await _db.ExecuteAsync(_deleteSql, new { Id = id });
}
