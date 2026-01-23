using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;
using Microsoft.EntityFrameworkCore;

namespace AgenticAITutor.Models;

public partial class notification_preference
{
    [Key]
    public Guid user_id { get; set; }

    public bool? reminder { get; set; }

    public bool? weak_topic { get; set; }

    public bool? quiz { get; set; }

    public bool? progress { get; set; }

    [ForeignKey("user_id")]
    [InverseProperty("notification_preference")]
    public virtual user user { get; set; } = null!;
}
