using System;
using Microsoft.EntityFrameworkCore.Migrations;
using Npgsql.EntityFrameworkCore.PostgreSQL.Metadata;

#nullable disable

namespace OtoEdit.Data.Migrations
{
    /// <inheritdoc />
    public partial class InitialCreate : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "endpoint_logs",
                columns: table => new
                {
                    id = table.Column<long>(type: "bigint", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityAlwaysColumn),
                    trace_id = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: true),
                    method = table.Column<string>(type: "character varying(10)", maxLength: 10, nullable: false),
                    path = table.Column<string>(type: "character varying(500)", maxLength: 500, nullable: false),
                    query = table.Column<string>(type: "character varying(1000)", maxLength: 1000, nullable: true),
                    request_body = table.Column<string>(type: "text", nullable: true),
                    response_body = table.Column<string>(type: "text", nullable: true),
                    status_code = table.Column<int>(type: "integer", nullable: false),
                    ip_address = table.Column<string>(type: "character varying(45)", maxLength: 45, nullable: true),
                    user_agent = table.Column<string>(type: "character varying(500)", maxLength: 500, nullable: true),
                    duration_ms = table.Column<int>(type: "integer", nullable: false),
                    created_at = table.Column<DateTime>(type: "timestamptz", nullable: false, defaultValueSql: "now()")
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_endpoint_logs", x => x.id);
                });

            migrationBuilder.CreateTable(
                name: "function_logs",
                columns: table => new
                {
                    id = table.Column<long>(type: "bigint", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityAlwaysColumn),
                    error_code = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    class_name = table.Column<string>(type: "character varying(200)", maxLength: 200, nullable: false),
                    method_name = table.Column<string>(type: "character varying(200)", maxLength: 200, nullable: false),
                    file_path = table.Column<string>(type: "character varying(500)", maxLength: 500, nullable: true),
                    line_number = table.Column<int>(type: "integer", nullable: false),
                    error_message = table.Column<string>(type: "text", nullable: true),
                    stack_trace = table.Column<string>(type: "text", nullable: true),
                    input_type = table.Column<string>(type: "character varying(200)", maxLength: 200, nullable: true),
                    input_value = table.Column<string>(type: "text", nullable: true),
                    trace_id = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: true),
                    severity = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: false, defaultValue: "Error"),
                    created_at = table.Column<DateTime>(type: "timestamptz", nullable: false, defaultValueSql: "now()")
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_function_logs", x => x.id);
                });

            migrationBuilder.CreateTable(
                name: "templates",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    ad = table.Column<string>(type: "character varying(200)", maxLength: 200, nullable: false),
                    tanim = table.Column<string>(type: "character varying(1000)", maxLength: 1000, nullable: true),
                    video_formati = table.Column<int>(type: "integer", nullable: false),
                    logo_yolu = table.Column<string>(type: "character varying(500)", maxLength: 500, nullable: true),
                    logo_pozisyonu = table.Column<string>(type: "jsonb", nullable: true),
                    konusmaci_ad_goster = table.Column<bool>(type: "boolean", nullable: false, defaultValue: false),
                    altyazi_stili = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: true),
                    altyazi_font = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: true),
                    altyazi_renk = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: true),
                    aktif_mi = table.Column<bool>(type: "boolean", nullable: false, defaultValue: true),
                    olusturma_tarihi = table.Column<DateTime>(type: "timestamptz", nullable: false, defaultValueSql: "now()")
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_templates", x => x.id);
                });

            migrationBuilder.CreateTable(
                name: "projects",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    ad = table.Column<string>(type: "character varying(200)", maxLength: 200, nullable: false),
                    aciklama = table.Column<string>(type: "character varying(2000)", maxLength: 2000, nullable: true),
                    video_formati = table.Column<int>(type: "integer", nullable: false, defaultValue: 0),
                    template_id = table.Column<Guid>(type: "uuid", nullable: true),
                    gesture_commands_enabled = table.Column<bool>(type: "boolean", nullable: false, defaultValue: true),
                    audio_enhancement_enabled = table.Column<bool>(type: "boolean", nullable: false, defaultValue: true),
                    durum = table.Column<int>(type: "integer", nullable: false, defaultValue: 0),
                    olusturma_tarihi = table.Column<DateTime>(type: "timestamptz", nullable: false, defaultValueSql: "now()"),
                    guncelleme_tarihi = table.Column<DateTime>(type: "timestamptz", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_projects", x => x.id);
                    table.ForeignKey(
                        name: "FK_projects_templates_template_id",
                        column: x => x.template_id,
                        principalTable: "templates",
                        principalColumn: "id",
                        onDelete: ReferentialAction.SetNull);
                });

            migrationBuilder.CreateTable(
                name: "chat_messages",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    project_id = table.Column<Guid>(type: "uuid", nullable: false),
                    rol = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: false),
                    mesaj = table.Column<string>(type: "text", nullable: false),
                    edl_patch = table.Column<string>(type: "jsonb", nullable: true),
                    olusturma_tarihi = table.Column<DateTime>(type: "timestamptz", nullable: false, defaultValueSql: "now()")
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_chat_messages", x => x.id);
                    table.ForeignKey(
                        name: "FK_chat_messages_projects_project_id",
                        column: x => x.project_id,
                        principalTable: "projects",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "edit_decision_lists",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    project_id = table.Column<Guid>(type: "uuid", nullable: false),
                    edl_json = table.Column<string>(type: "jsonb", nullable: false, defaultValue: "{}"),
                    versiyon = table.Column<int>(type: "integer", nullable: false, defaultValue: 1),
                    olusturma_tarihi = table.Column<DateTime>(type: "timestamptz", nullable: false, defaultValueSql: "now()"),
                    guncelleme_tarihi = table.Column<DateTime>(type: "timestamptz", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_edit_decision_lists", x => x.id);
                    table.ForeignKey(
                        name: "FK_edit_decision_lists_projects_project_id",
                        column: x => x.project_id,
                        principalTable: "projects",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "render_jobs",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    project_id = table.Column<Guid>(type: "uuid", nullable: false),
                    edl_snapshot = table.Column<string>(type: "jsonb", nullable: false),
                    durum = table.Column<int>(type: "integer", nullable: false, defaultValue: 0),
                    cikti_yolu = table.Column<string>(type: "character varying(500)", maxLength: 500, nullable: true),
                    baslangic_zamani = table.Column<DateTime>(type: "timestamptz", nullable: false, defaultValueSql: "now()"),
                    bitis_zamani = table.Column<DateTime>(type: "timestamptz", nullable: true),
                    sure_ms = table.Column<int>(type: "integer", nullable: true),
                    hata_mesaji = table.Column<string>(type: "text", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_render_jobs", x => x.id);
                    table.ForeignKey(
                        name: "FK_render_jobs_projects_project_id",
                        column: x => x.project_id,
                        principalTable: "projects",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "videos",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    project_id = table.Column<Guid>(type: "uuid", nullable: false),
                    baslik = table.Column<string>(type: "character varying(300)", maxLength: 300, nullable: false),
                    dosya_yolu = table.Column<string>(type: "character varying(500)", maxLength: 500, nullable: false),
                    temiz_ses_yolu = table.Column<string>(type: "character varying(500)", maxLength: 500, nullable: true),
                    sure = table.Column<TimeSpan>(type: "interval", nullable: true),
                    dosya_boyutu = table.Column<long>(type: "bigint", nullable: false, defaultValue: 0L),
                    islem_durumu = table.Column<int>(type: "integer", nullable: false, defaultValue: 0),
                    olusturma_tarihi = table.Column<DateTime>(type: "timestamptz", nullable: false, defaultValueSql: "now()"),
                    islem_tamamlanma_tarihi = table.Column<DateTime>(type: "timestamptz", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_videos", x => x.id);
                    table.ForeignKey(
                        name: "FK_videos_projects_project_id",
                        column: x => x.project_id,
                        principalTable: "projects",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "pipeline_logs",
                columns: table => new
                {
                    id = table.Column<long>(type: "bigint", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityAlwaysColumn),
                    video_id = table.Column<Guid>(type: "uuid", nullable: true),
                    project_id = table.Column<Guid>(type: "uuid", nullable: true),
                    render_job_id = table.Column<Guid>(type: "uuid", nullable: true),
                    asama = table.Column<int>(type: "integer", nullable: false),
                    durum = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: false),
                    baslangic_zamani = table.Column<DateTime>(type: "timestamptz", nullable: false, defaultValueSql: "now()"),
                    bitis_zamani = table.Column<DateTime>(type: "timestamptz", nullable: true),
                    sure_ms = table.Column<int>(type: "integer", nullable: true),
                    hata_mesaji = table.Column<string>(type: "text", nullable: true),
                    hata_detayi = table.Column<string>(type: "text", nullable: true),
                    girdi_metadata = table.Column<string>(type: "jsonb", nullable: true),
                    cikti_metadata = table.Column<string>(type: "jsonb", nullable: true),
                    trace_id = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: true),
                    created_at = table.Column<DateTime>(type: "timestamptz", nullable: false, defaultValueSql: "now()")
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_pipeline_logs", x => x.id);
                    table.ForeignKey(
                        name: "FK_pipeline_logs_projects_project_id",
                        column: x => x.project_id,
                        principalTable: "projects",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                    table.ForeignKey(
                        name: "FK_pipeline_logs_videos_video_id",
                        column: x => x.video_id,
                        principalTable: "videos",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "video_transcripts",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    video_id = table.Column<Guid>(type: "uuid", nullable: false),
                    ham_metin = table.Column<string>(type: "text", nullable: false),
                    zaman_damgalari = table.Column<string>(type: "jsonb", nullable: true),
                    dil = table.Column<string>(type: "character varying(10)", maxLength: 10, nullable: false, defaultValue: "tr"),
                    kelime_sayisi = table.Column<int>(type: "integer", nullable: false, defaultValue: 0),
                    stt_model = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    stt_suresi_ms = table.Column<int>(type: "integer", nullable: false, defaultValue: 0),
                    olusturma_tarihi = table.Column<DateTime>(type: "timestamptz", nullable: false, defaultValueSql: "now()")
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_video_transcripts", x => x.id);
                    table.ForeignKey(
                        name: "FK_video_transcripts_videos_video_id",
                        column: x => x.video_id,
                        principalTable: "videos",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateIndex(
                name: "idx_chat_messages_olusturma",
                table: "chat_messages",
                column: "olusturma_tarihi");

            migrationBuilder.CreateIndex(
                name: "idx_chat_messages_project_id",
                table: "chat_messages",
                column: "project_id");

            migrationBuilder.CreateIndex(
                name: "idx_edl_project_id",
                table: "edit_decision_lists",
                column: "project_id",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "idx_endpoint_logs_created_at",
                table: "endpoint_logs",
                column: "created_at",
                descending: new bool[0]);

            migrationBuilder.CreateIndex(
                name: "idx_endpoint_logs_path",
                table: "endpoint_logs",
                column: "path");

            migrationBuilder.CreateIndex(
                name: "idx_endpoint_logs_status_code",
                table: "endpoint_logs",
                column: "status_code");

            migrationBuilder.CreateIndex(
                name: "idx_function_logs_created_at",
                table: "function_logs",
                column: "created_at",
                descending: new bool[0]);

            migrationBuilder.CreateIndex(
                name: "idx_function_logs_error_code",
                table: "function_logs",
                column: "error_code");

            migrationBuilder.CreateIndex(
                name: "idx_function_logs_severity",
                table: "function_logs",
                column: "severity");

            migrationBuilder.CreateIndex(
                name: "idx_pipeline_logs_asama",
                table: "pipeline_logs",
                column: "asama");

            migrationBuilder.CreateIndex(
                name: "idx_pipeline_logs_created_at",
                table: "pipeline_logs",
                column: "created_at",
                descending: new bool[0]);

            migrationBuilder.CreateIndex(
                name: "idx_pipeline_logs_project_id",
                table: "pipeline_logs",
                column: "project_id");

            migrationBuilder.CreateIndex(
                name: "idx_pipeline_logs_video_id",
                table: "pipeline_logs",
                column: "video_id");

            migrationBuilder.CreateIndex(
                name: "IX_projects_template_id",
                table: "projects",
                column: "template_id");

            migrationBuilder.CreateIndex(
                name: "idx_projects_durum",
                table: "projects",
                column: "durum");

            migrationBuilder.CreateIndex(
                name: "idx_projects_olusturma",
                table: "projects",
                column: "olusturma_tarihi",
                descending: new bool[0]);

            migrationBuilder.CreateIndex(
                name: "idx_render_jobs_durum",
                table: "render_jobs",
                column: "durum");

            migrationBuilder.CreateIndex(
                name: "idx_render_jobs_project_id",
                table: "render_jobs",
                column: "project_id");

            migrationBuilder.CreateIndex(
                name: "idx_video_transcripts_video_id",
                table: "video_transcripts",
                column: "video_id",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "idx_videos_durum",
                table: "videos",
                column: "islem_durumu");

            migrationBuilder.CreateIndex(
                name: "idx_videos_project_id",
                table: "videos",
                column: "project_id",
                unique: true);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "chat_messages");

            migrationBuilder.DropTable(
                name: "edit_decision_lists");

            migrationBuilder.DropTable(
                name: "endpoint_logs");

            migrationBuilder.DropTable(
                name: "function_logs");

            migrationBuilder.DropTable(
                name: "pipeline_logs");

            migrationBuilder.DropTable(
                name: "render_jobs");

            migrationBuilder.DropTable(
                name: "video_transcripts");

            migrationBuilder.DropTable(
                name: "videos");

            migrationBuilder.DropTable(
                name: "projects");

            migrationBuilder.DropTable(
                name: "templates");
        }
    }
}
