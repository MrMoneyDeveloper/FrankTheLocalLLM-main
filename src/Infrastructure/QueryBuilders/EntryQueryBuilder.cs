using System.Text;
using Dapper;
using Domain.Interfaces;

namespace Infrastructure.QueryBuilders;

public class EntryQueryBuilder
{
    private readonly EntryQueryOptions _options;

    public EntryQueryBuilder(EntryQueryOptions options)
    {
        _options = options;
    }

    public (string Sql, DynamicParameters Parameters) Build()
    {
        var sb = new StringBuilder("SELECT id as Id, user_id as UserId, content as Content, tags as Tags, created_at as CreatedAt FROM entries");
        var conditions = new List<string>();
        var parameters = new DynamicParameters();
        if (_options.Tags != null && _options.Tags.Any())
        {
            int idx = 0;
            foreach (var tag in _options.Tags)
            {
                var name = $"tag{idx}";
                conditions.Add($"tags LIKE @{name}");
                parameters.Add(name, $"%{tag}%");
                idx++;
            }
        }
        if (_options.From.HasValue)
        {
            conditions.Add("created_at >= @from");
            parameters.Add("from", _options.From.Value);
        }
        if (_options.To.HasValue)
        {
            conditions.Add("created_at <= @to");
            parameters.Add("to", _options.To.Value);
        }
        if (!string.IsNullOrEmpty(_options.Text))
        {
            conditions.Add("content LIKE @text");
            parameters.Add("text", $"%{_options.Text}%");
        }

        if (conditions.Count > 0)
        {
            sb.Append(" WHERE ").Append(string.Join(" AND ", conditions));
        }

        return (sb.ToString(), parameters);
    }
}
