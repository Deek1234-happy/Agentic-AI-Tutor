/* 
 Database Scaffolding Command
  Scaffold-DbContext "Host=localhost;Port=5432;Database=AgenticAITutor;Username=postgres;Password=8105" Npgsql.EntityFrameworkCore.PostgreSQL -OutputDir Models -Context AppDbContext -ContextDir Data -DataAnnotations -Force -NoOnConfiguring -Schemas public,auth,content,planner,quiz,rag
 */

using AgenticAITutor.BackgroundJobs;
using AgenticAITutor.Data;
using AgenticAITutor.Filters;
using AgenticAITutor.Helpers;
using AgenticAITutor.Repositories;
using AgenticAITutor.Services;
using FluentValidation;
using Hangfire;
using Hangfire.PostgreSql;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.AspNetCore.Http.Features;
using Microsoft.EntityFrameworkCore;
using Microsoft.IdentityModel.Tokens;
using Microsoft.OpenApi.Models;
using Npgsql;
using Pgvector.Npgsql;
using Polly;
using SharpGrip.FluentValidation.AutoValidation.Mvc.Extensions;
using System.Text;


namespace AgenticAITutor
{
    public class Program
    {
        public static void Main(string[] args)
        {
            AppDomain.CurrentDomain.FirstChanceException += (sender, e) =>
            {

                // 1. Ignore the harmless PostgreSQL IPv6 fallback noise
                if (e.Exception is System.Net.Sockets.SocketException socketEx &&
                    socketEx.Message.Contains("[::1]:5432"))
                {
                    return; // Exit early, do not log
                }

                // Only log "serious" exceptions, skip common noise
                if (e.Exception is OutOfMemoryException
                    || e.Exception is AccessViolationException
                    || e.Exception is StackOverflowException
                    || e.Exception is System.Net.Sockets.SocketException
                    || e.Exception is Npgsql.NpgsqlException
                    || e.Exception is Npgsql.PostgresException)
                {
                    Console.WriteLine($"[FIRST-CHANCE] {e.Exception.GetType().Name}: {e.Exception.Message}");
                }
            };


            var builder = WebApplication.CreateBuilder(args);

            // Add services to the container.

            builder.Services.AddControllers();
            // Learn more about configuring Swagger/OpenAPI at https://aka.ms/aspnetcore/swashbuckle
            builder.Services.AddEndpointsApiExplorer();
            builder.Services.AddSwaggerGen(options =>
            {
                var jwtSecurityScheme = new OpenApiSecurityScheme
                {
                    BearerFormat = "JWT",
                    Name = "Authorization",
                    In = ParameterLocation.Header,
                    Type = SecuritySchemeType.Http,
                    Scheme = JwtBearerDefaults.AuthenticationScheme,
                    Description = "Enter Your JWT Access Token",
                    Reference = new OpenApiReference
                    {
                        Id = JwtBearerDefaults.AuthenticationScheme,
                        Type = ReferenceType.SecurityScheme
                    }
                };
                options.AddSecurityDefinition("Bearer", jwtSecurityScheme);
                options.AddSecurityRequirement(new OpenApiSecurityRequirement
                {
                    {jwtSecurityScheme, Array.Empty<string>() }
                });
                options.SwaggerDoc("v1", new OpenApiInfo()
                {
                    Version = "v1",
                    Title = "Agentic AI Tutor APIs"
                });
                var filePath = Path.Combine(System.AppContext.BaseDirectory, "ApiDoc.xml");
                options.IncludeXmlComments(filePath);

            });

            // -----------------------------------
            var dataSourceBuilder = new NpgsqlDataSourceBuilder(builder.Configuration.GetConnectionString("DefaultConnection"));
            dataSourceBuilder.UseVector();
            //dataSourceBuilder.ConnectionStringBuilder.MaxPoolSize = 5; ////////////////////////////////////////////////////////
            var dataSource = dataSourceBuilder.Build();
            builder.Services.AddSingleton(dataSource);
            builder.Services.AddDbContext<AppDbContext>(options =>
            {
                options.UseNpgsql(dataSource, x=>x.UseVector());
            });
            // -----------------------------------


            //builder.Services.AddDbContext<AppDbContext>(options =>
            //{
            //    options.UseNpgsql(builder.Configuration.GetConnectionString("DefaultConnection"),
            //    o => o.UseVector());
            //});

            builder.Services.AddScoped<IUserRepository, UserRepository>();
            builder.Services.AddScoped<IAuthService, AuthService>();
            builder.Services.AddTransient<IEmailService, SmtpEmailService>();

            builder.Services.Configure<JWT>(builder.Configuration.GetSection("JWT")); // Map Values In JWT Section In That JWT Class


            builder.Services.AddAuthentication(options =>
            {
                options.DefaultAuthenticateScheme = JwtBearerDefaults.AuthenticationScheme;
                options.DefaultChallengeScheme = JwtBearerDefaults.AuthenticationScheme;
            }).AddJwtBearer(op =>
            {
                op.RequireHttpsMetadata = false;
                op.SaveToken = false;
                op.TokenValidationParameters = new TokenValidationParameters
                {
                    ValidateIssuerSigningKey = true,
                    ValidateIssuer = true,
                    ValidateAudience = true,
                    ValidateLifetime = true,
                    ValidIssuer = builder.Configuration["JWT:Issuer"],
                    ValidAudience = builder.Configuration["JWT:Audience"],
                    IssuerSigningKey = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(builder.Configuration["JWT:Key"]))
                };
            });

            builder.Services.AddScoped<IPasswordHasher, BCryptPasswordHasher>();

            // Fluent Validation Services 
            builder.Services.AddValidatorsFromAssemblyContaining<Program>();
            builder.Services.AddFluentValidationAutoValidation();

            builder.Services.AddScoped<ISubjectRepository, SubjectRepository>();
            builder.Services.AddScoped<ISubjectService, SubjectService>();

            builder.Services.AddScoped<IDocumentRepository, DocumentRepository>();
            builder.Services.AddScoped<IFileStorageService, LocalFileStorageService>();
            builder.Services.AddScoped<IDocumentService, DocumentService>();


            // Hangfire
            builder.Services.AddHangfire(config =>
                config.UsePostgreSqlStorage(c => c.UseNpgsqlConnection(builder.Configuration.GetConnectionString("DefaultConnection")))
            );

            builder.Services.AddHangfireServer(options =>
            {
                options.WorkerCount = 2; // Use only 2 workers instead of the default 20
            });

            builder.Services.AddScoped<IDocumentChunkRepository, DocumentChunkRepository>();    
            builder.Services.AddScoped<IDocumentChunkService, DocumentChunkService>();
            builder.Services.AddTransient<DocumentChunkingJob>();

            builder.Services.AddCors(options =>
            {
                options.AddPolicy("AllowAll", policy =>
                {
                    policy.AllowAnyOrigin().AllowAnyMethod().AllowAnyHeader();

                });
            });

            builder.Services.AddScoped<IUserService, UserService>();

            
            builder.Services.AddScoped<IChatSessionRepository, ChatSessionRepository>();
            builder.Services.AddScoped<IChatSessionService, ChatSessionService>();

            builder.Services.AddScoped<IChatMessageRepository, ChatMessageRepository>();
            builder.Services.AddScoped<IChatMessageService, ChatMessageService>();

            builder.Services.AddScoped<IChatWebSourceRepository, ChatWebSourceRepository>();

            // ── Quiz Agent ────────────────────────────────────────────────────
            builder.Services.AddScoped<IQuizRepository, QuizRepository>();
            builder.Services.AddScoped<IGenerationHashService, GenerationHashService>();
            builder.Services.AddScoped<IQuizService, QuizService>();
            builder.Services.AddScoped<IQuizAIClient, QuizAIClient>();
            builder.Services.AddTransient<QuizGenerationJob>();
            // ─────────────────────────────────────────────────────────────────


            // builder.Services.AddHttpClient();

            builder.Services.AddHttpClient(nameof(ChatMessageService), client =>
            {
                client.Timeout = TimeSpan.FromMinutes(10);
                client.DefaultRequestHeaders.Add("ngrok-skip-browser-warning", "true"); // Comment Me
            });

            builder.Services.AddHttpClient(nameof(DocumentChunkService), client =>
            {
                client.Timeout = TimeSpan.FromMinutes(10);
                client.DefaultRequestHeaders.Add("ngrok-skip-browser-warning", "true"); // Comment Me
            });

            builder.Services.AddHttpClient(nameof(DocumentService));
            builder.Services.AddHttpClient(nameof(SubjectService));

            // Quiz AI client: 120s timeout + Polly retry (3 attempts, exponential back-off)
            builder.Services.AddHttpClient("QuizAIClient", client =>
            {
                client.DefaultRequestHeaders.Add("ngrok-skip-browser-warning", "true"); // Comment Me
                client.Timeout = TimeSpan.FromMinutes(10);
            });
            //.AddTransientHttpErrorPolicy(policy =>
            //    policy.WaitAndRetryAsync(
            //        retryCount: 3,
            //        sleepDurationProvider: attempt => TimeSpan.FromSeconds(Math.Pow(2, attempt)),
            //        onRetry: (outcome, timespan, attempt, _) =>
            //        {
            //            Console.WriteLine(
            //                $"[QuizAIClient] Retry {attempt} after {timespan.TotalSeconds:F1}s. Reason: {outcome.Exception?.Message ?? outcome.Result?.StatusCode.ToString()}");
            //        }));

            builder.Services.Configure<FormOptions>(options =>
            {
                options.MultipartBodyLengthLimit = 10 * 1024 * 1024; // Match your 10 MB business rule
            });

            builder.WebHost.ConfigureKestrel(options =>
            {
                options.Limits.MaxRequestBodySize = 10 * 1024 * 1024;
            });

            builder.Services.AddScoped<IQuizChunkRepository, QuizChunkRepository>();


            var app = builder.Build();

            app.UseCors("AllowAll");

            app.UseHangfireDashboard("/dashboard", new DashboardOptions
            {
                Authorization = new[] { new HangfireAuthorizationFilter() }
            });

            // Configure the HTTP request pipeline.
            //if (app.Environment.IsDevelopment())
            //{
            app.UseSwagger();
            app.UseSwaggerUI(options =>
            {
                // Sort endpoints by HTTP method (GET, POST, PUT, DELETE) within their tags
                options.ConfigObject.AdditionalItems["operationsSorter"] = "method";
            });
            //}

            
            app.UseHttpsRedirection();
            

            app.UseStaticFiles();

            app.UseAuthentication(); 
            app.UseAuthorization();


            app.MapControllers();

            app.Run();
        }
    }
}
