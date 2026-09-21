using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace OtoEdit.Data.Migrations
{
    /// <inheritdoc />
    public partial class AddEdlSnapshots : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<string>(
                name: "patch_durumu",
                table: "chat_messages",
                type: "character varying(20)",
                maxLength: 20,
                nullable: false,
                defaultValue: "none");

            migrationBuilder.AddColumn<string>(
                name: "pending_edl_patch",
                table: "chat_messages",
                type: "jsonb",
                nullable: true);

            migrationBuilder.CreateTable(
                name: "edl_snapshots",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    project_id = table.Column<Guid>(type: "uuid", nullable: false),
                    versiyon = table.Column<int>(type: "integer", nullable: false),
                    edl_json = table.Column<string>(type: "jsonb", nullable: false),
                    aciklama = table.Column<string>(type: "character varying(255)", maxLength: 255, nullable: true),
                    kaynak = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    olusturma_tarihi = table.Column<DateTime>(type: "timestamptz", nullable: false, defaultValueSql: "now()")
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_edl_snapshots", x => x.id);
                    table.ForeignKey(
                        name: "fk_edl_snapshots_projects",
                        column: x => x.project_id,
                        principalTable: "projects",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateIndex(
                name: "idx_edl_snapshots_project_id",
                table: "edl_snapshots",
                column: "project_id");

            migrationBuilder.CreateIndex(
                name: "idx_edl_snapshots_project_id_versiyon",
                table: "edl_snapshots",
                columns: new[] { "project_id", "versiyon" },
                unique: true);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "edl_snapshots");

            migrationBuilder.DropColumn(
                name: "patch_durumu",
                table: "chat_messages");

            migrationBuilder.DropColumn(
                name: "pending_edl_patch",
                table: "chat_messages");
        }
    }
}
