using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;
using Microsoft.EntityFrameworkCore;

namespace AgenticAITutorDeom.Models;

[Table("users", Schema = "auth")]
[Index("email", Name = "users_email_key", IsUnique = true)]
public partial class user
{
    [Key]
    public Guid id { get; set; }

    [StringLength(255)]
    public string first_name { get; set; } = null!;

    [StringLength(255)]
    public string last_name { get; set; } = null!;

    [StringLength(255)]
    public string email { get; set; } = null!;

    public string password_hash { get; set; } = null!;

    [StringLength(50)]
    public string? role { get; set; }

    [Column(TypeName = "timestamp without time zone")]
    public DateTime? created_at { get; set; }

    [Column(TypeName = "timestamp without time zone")]
    public DateTime? last_login { get; set; }

    [InverseProperty("user")]
    public virtual ICollection<activity_log> activity_logs { get; set; } = new List<activity_log>();

    [InverseProperty("user")]
    public virtual ICollection<chat_session> chat_sessions { get; set; } = new List<chat_session>();

    [InverseProperty("user")]
    public virtual ICollection<document> documents { get; set; } = new List<document>();

    [InverseProperty("user")]
    public virtual notification_preference? notification_preference { get; set; }

    [InverseProperty("user")]
    public virtual ICollection<notification> notifications { get; set; } = new List<notification>();

    [InverseProperty("user")]
    public virtual ICollection<quiz_attempt> quiz_attempts { get; set; } = new List<quiz_attempt>();

    [InverseProperty("user")]
    public virtual ICollection<quiz> quizzes { get; set; } = new List<quiz>();

    [InverseProperty("user")]
    public virtual ICollection<study_plan> study_plans { get; set; } = new List<study_plan>();

    [InverseProperty("user")]
    public virtual ICollection<user_topic_progress> user_topic_progresses { get; set; } = new List<user_topic_progress>();
}
