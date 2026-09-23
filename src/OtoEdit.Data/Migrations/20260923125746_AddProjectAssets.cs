using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace OtoEdit.Data.Migrations
{
    /// <inheritdoc />
    public partial class AddProjectAssets : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "ProjectAssets",
                columns: table => new
                {
                    Id = table.Column<Guid>(type: "uuid", nullable: false),
                    ProjectId = table.Column<Guid>(type: "uuid", nullable: false),
                    DosyaAdi = table.Column<string>(type: "text", nullable: false),
                    MimeTuru = table.Column<string>(type: "text", nullable: false),
                    StorageKey = table.Column<string>(type: "text", nullable: false),
                    Url = table.Column<string>(type: "text", nullable: false),
                    BoyutByte = table.Column<long>(type: "bigint", nullable: false),
                    YuklemeTarihi = table.Column<DateTime>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_ProjectAssets", x => x.Id);
                    table.ForeignKey(
                        name: "FK_ProjectAssets_projects_ProjectId",
                        column: x => x.ProjectId,
                        principalTable: "projects",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateIndex(
                name: "IX_ProjectAssets_ProjectId",
                table: "ProjectAssets",
                column: "ProjectId");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "ProjectAssets");
        }
    }
}
