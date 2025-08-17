using Domain.Entities;

namespace Domain.Interfaces;

public class EntryQueryOptions
{
    public IEnumerable<string>? Tags { get; set; }
    public DateTime? From { get; set; }
    public DateTime? To { get; set; }
    public string? Text { get; set; }
}

public interface IEntryRepository
{
    Task InitializeAsync();
    Task<int> AddAsync(Entry entry);
    Task<IEnumerable<Entry>> QueryAsync(EntryQueryOptions options);
}
