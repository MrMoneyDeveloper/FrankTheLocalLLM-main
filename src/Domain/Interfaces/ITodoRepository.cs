using Domain.Entities;

namespace Domain.Interfaces;

public interface ITodoRepository
{
    Task InitializeAsync();
    Task<int> AddAsync(TodoItem item);
    Task<IEnumerable<TodoItem>> GetAllAsync();
}
