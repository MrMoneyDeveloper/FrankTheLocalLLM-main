namespace Domain.Entities;

public class Entry : BaseEntity
{
    public int UserId { get; set; }
    public string Content { get; set; } = string.Empty;
    public string Tags { get; set; } = string.Empty;
    public DateTime CreatedAt { get; set; }
}
