// openutau-render: .ustx -> .wav sin abrir la interfaz de OpenUtau.
// Uso:  dotnet run --project OpenUtau.Render -c Release -- entrada.ustx salida.wav
using System.Collections.Concurrent;
using System.Text;
using OpenUtau.Classic;
using OpenUtau.Core;
using OpenUtau.Core.Format;
using OpenUtau.Core.Ustx;
using OpenUtau.Core.Util;

if (args.Length < 2) {
    Console.Error.WriteLine("uso: openutau-render entrada.ustx salida.wav");
    return 2;
}
Encoding.RegisterProvider(CodePagesEncodingProvider.Instance);

// Cola que hace de "hilo de interfaz": OpenUtau reenvía comandos desde hilos de fondo
// con PostOnUIThread; sin esto daba NullReferenceException.
var cola = new BlockingCollection<Action>();
DocManager.Inst.PostOnUIThread = a => cola.Add(a);

ToolsManager.Inst.Initialize();
DocManager.Inst.Initialize(Thread.CurrentThread, TaskScheduler.Default);
DocManager.Inst.PostOnUIThread = a => cola.Add(a);   // Initialize puede reiniciarlo
SingerManager.Inst.Initialize();
DocManager.Inst.AddSubscriber(new Mostrar());

var project = Ustx.Load(Path.GetFullPath(args[0]));
DocManager.Inst.ExecuteCmd(new LoadProjectNotification(project));
// Espera (hasta 20 s) a que fonemizador y constructor de frases terminen, bombeando la cola
// del "hilo de interfaz": sus resultados llegan por ahí y con Sleep nunca se procesaban.
var limite = DateTime.UtcNow.AddSeconds(20);
while (DateTime.UtcNow < limite) {
    while (cola.TryTake(out var pendiente)) pendiente();
    var partes = project.parts.OfType<UVoicePart>().ToList();
    if (partes.Count > 0 && partes.All(p => p.renderPhrases.Count > 0)) break;
    Thread.Sleep(50);
}

// --- Diagnóstico ---
Console.WriteLine($"Carpetas de cantantes: {string.Join(", ", PathManager.Inst.SingersPaths)}");
Console.WriteLine($"Cantantes encontrados: {SingerManager.Inst.Singers.Count}");
foreach (var t in project.tracks)
    Console.WriteLine($"Pista '{t.TrackName}': cantante cargado = {(t.Singer == null ? "NO" : t.Singer.Id)}");
foreach (var t in project.tracks)
    if (t.Singer != null)
        Console.WriteLine($"Cantante: tipo={t.Singer.SingerType}, encontrado={t.Singer.Found}, cargado={t.Singer.Loaded}, ruta={t.Singer.Location}");
foreach (var p in project.parts.OfType<UVoicePart>())
    foreach (var f in p.phonemes)
        Console.WriteLine($"  Fonema '{f.phoneme}' error={f.Error} {(f.ErrorException != null ? f.ErrorException.Message : "")}");
foreach (var p in project.parts.OfType<UVoicePart>())
    Console.WriteLine($"Parte '{p.name}': notas = {p.notes.Count}, fonemas = {p.phonemes.Count}, frases = {p.renderPhrases.Count}");

var salida = Path.GetFullPath(args[1]);
var tarea = PlaybackManager.Inst.RenderMixdown(project, salida);
while (!tarea.IsCompleted) {
    if (cola.TryTake(out var a, 50)) a();   // bombea comandos en el hilo principal
}
while (cola.TryTake(out var resto)) resto();
await tarea;

Console.WriteLine(File.Exists(salida) ? $"OK {salida}" : "FALLÓ: no se creó el wav");
return File.Exists(salida) ? 0 : 1;

// Imprime errores y progreso para ver qué falla de verdad.
class Mostrar : ICmdSubscriber {
    public void OnNext(UCommand cmd, bool isUndo) {
        if (cmd is ErrorMessageNotification e) {
            Console.Error.WriteLine("ERROR: " + e.message);
            if (e.e != null) Console.Error.WriteLine(e.e);
        } else if (cmd is ProgressBarNotification p && !string.IsNullOrEmpty(p.Info)) {
            Console.WriteLine(p.Info);
        }
    }
}
