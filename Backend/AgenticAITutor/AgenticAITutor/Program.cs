/* 
 Database Scaffolding Command
  Scaffold-DbContext "Host=localhost;Port=5432;Database=AgenticAITutor;Username=postgres;Password=8105" Npgsql.EntityFrameworkCore.PostgreSQL -OutputDir Models -Context AppDbContext -ContextDir Data -DataAnnotations -Force -NoOnConfiguring -Schemas public,auth,content,planner,quiz,rag
 */

using AgenticAITutor.Data;
using AgenticAITutor.Helpers;
using AgenticAITutor.Repositories;
using AgenticAITutor.Services;
using FluentValidation;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.EntityFrameworkCore;
using Microsoft.IdentityModel.Tokens;
using System.Text;
using SharpGrip.FluentValidation.AutoValidation.Mvc.Extensions;
using Hangfire;
using Hangfire.PostgreSql;
using AgenticAITutor.BackgroundJobs;

using Npgsql;
using Pgvector.Npgsql;
using AgenticAITutor.Filters;
using Microsoft.OpenApi.Models;


namespace AgenticAITutor
{
    public class Program
    {
        public static void Main(string[] args)
        {
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

            builder.Services.AddHangfire(config =>
                config.UsePostgreSqlStorage(c => c.UseNpgsqlConnection(builder.Configuration.GetConnectionString("DefaultConnection")))
            );
            builder.Services.AddHangfireServer();

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


            builder.Services.AddHttpClient();

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
                app.UseSwaggerUI();
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
