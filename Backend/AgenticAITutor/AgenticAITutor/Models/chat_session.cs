using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;
using Microsoft.EntityFrameworkCore;

namespace AgenticAITutor.Models;

[Table("chat_sessions", Schema = "rag")]
public partial class chat_session
{
    [Key]
    public Guid id { get; set; }

    public Guid? user_id { get; set; }

    [Column(TypeName = "timestamp without time zone")]
    public DateTime? started_at { get; set; }

    [InverseProperty("session")]
    public virtual ICollection<chat_message> chat_messages { get; set; } = new List<chat_message>();

    [ForeignKey("user_id")]
    [InverseProperty("chat_sessions")]
    public virtual user? user { get; set; }
}
