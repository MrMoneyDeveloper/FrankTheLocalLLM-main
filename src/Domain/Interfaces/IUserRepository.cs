using Domain.Entities;

namespace Domain.Interfaces;

public interface IUserRepository
{
    Task InitializeAsync();
    Task<int> AddAsync(User user);
    Task<User?> GetByIdAsync(int id);
    Task<User?> GetByUsernameAsync(string username);
    Task<IEnumerable<User>> GetAllAsync();
    Task UpdateAsync(User user);
    Task DeleteAsync(int id);
    Task<UserStats?> GetStatsAsync(int userId);
}

public class UserStats
{
    public int UserId { get; set; }
    public string Username { get; set; } = string.Empty;
    public int EntryCount { get; set; }
    public int TaskCount { get; set; }
}
