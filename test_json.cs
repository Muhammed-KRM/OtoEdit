using System;
using System.Text.Json;
using System.Text.Json.Nodes;

class Program {
    static void Main() {
        var json = @"{ ""transcript"": { ""segments"": [ { ""text"": ""old"" } ] } }";
        var rootNode = JsonNode.Parse(json).AsObject();
        
        var patchJson = @"{ ""transcript"": { ""segments"": [ { ""text"": ""new"" } ] } }";
        var patchDoc = JsonDocument.Parse(patchJson);
        foreach (var property in patchDoc.RootElement.EnumerateObject()) {
            var patchValueNode = JsonNode.Parse(property.Value.GetRawText());
            rootNode[property.Name] = patchValueNode;
        }
        
        Console.WriteLine(rootNode.ToJsonString());
    }
}
