# ============================================================
# run.ps1 — Script PowerShell utilitaire pour BotAlert
# ============================================================
# EXPLICATION :
#   Au lieu de mémoriser des dizaines de commandes docker-compose,
#   ce script regroupe toutes les opérations courantes en une
#   seule interface simple. C'est ce qu'on appelle un "wrapper".
#
# USAGE :
#   .\run.ps1 start          → Démarrer toute l'infrastructure
#   .\run.ps1 stop           → Arrêter tous les services
#   .\run.ps1 logs           → Voir les logs en direct
#   .\run.ps1 fleet 500      → Lancer 500 maisons simulées
#   .\run.ps1 status         → État de tous les services
#   .\run.ps1 reset          → Tout effacer et repartir de zéro
#   .\run.ps1 chaos          → Test de résilience (bonus démo)
# ============================================================

param(
    [Parameter(Position=0)]
    [string]$Command = "help",

    [Parameter(Position=1)]
    [int]$Devices = 1
)

function Print-Header {
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host "   BotAlert DevOps Tools — M. Guergari   " -ForegroundColor Cyan
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host ""
}

function Start-Stack {
    Write-Host "🚀 Démarrage de toute l'infrastructure..." -ForegroundColor Green
    docker-compose up -d --build
    Write-Host ""
    Write-Host "✅ Services disponibles :" -ForegroundColor Green
    Write-Host "   Grafana   → http://localhost:3000  (admin/admin_secret)" -ForegroundColor Yellow
    Write-Host "   API       → http://localhost:8000/docs" -ForegroundColor Yellow
    Write-Host "   MQTT      → localhost:1883" -ForegroundColor Yellow
    Write-Host "   TimescaleDB → localhost:5432" -ForegroundColor Yellow
}

function Stop-Stack {
    Write-Host "🛑 Arrêt de tous les services..." -ForegroundColor Red
    docker-compose stop
    Write-Host "✅ Services arrêtés." -ForegroundColor Green
}

function Show-Status {
    Write-Host "📊 État des services :" -ForegroundColor Cyan
    docker-compose ps
}

function Show-Logs {
    param([string]$Service = "")
    if ($Service -eq "") {
        Write-Host "📋 Logs de tous les services (Ctrl+C pour quitter) :" -ForegroundColor Cyan
        docker-compose logs -f
    } else {
        Write-Host "📋 Logs de '$Service' (Ctrl+C pour quitter) :" -ForegroundColor Cyan
        docker-compose logs -f $Service
    }
}

function Start-Fleet {
    param([int]$N = 100)
    Write-Host "🌍 Démarrage Fleet Mode : $N maisons..." -ForegroundColor Magenta
    $env:NUM_DEVICES = $N
    docker-compose up -d --build simulator
    Write-Host "✅ Simulateur lancé avec $N appareils." -ForegroundColor Green
    Write-Host "   Pour voir les stats : .\run.ps1 logs simulator" -ForegroundColor Yellow
}

function Reset-Stack {
    Write-Host "⚠️  ATTENTION : Cela va effacer TOUTES les données !" -ForegroundColor Red
    $confirm = Read-Host "Confirmer ? (oui/non)"
    if ($confirm -eq "oui") {
        Write-Host "🗑️  Suppression des conteneurs et volumes..." -ForegroundColor Red
        docker-compose down -v
        Write-Host "✅ Reset terminé. Lancer '.\run.ps1 start' pour repartir." -ForegroundColor Green
    } else {
        Write-Host "❌ Reset annulé." -ForegroundColor Yellow
    }
}

function Run-Chaos {
    Write-Host "💥 Lancement du test de résilience..." -ForegroundColor Red
    python infra/chaos_test.py
}

function Show-Help {
    Write-Host "COMMANDES DISPONIBLES :" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  .\run.ps1 start              Démarrer toute l'infrastructure" -ForegroundColor White
    Write-Host "  .\run.ps1 stop               Arrêter tous les services" -ForegroundColor White
    Write-Host "  .\run.ps1 status             Voir l'état des conteneurs" -ForegroundColor White
    Write-Host "  .\run.ps1 logs               Voir tous les logs en direct" -ForegroundColor White
    Write-Host "  .\run.ps1 logs simulator     Logs du simulateur uniquement" -ForegroundColor White
    Write-Host "  .\run.ps1 logs backend       Logs du backend uniquement" -ForegroundColor White
    Write-Host "  .\run.ps1 fleet 100          Lancer 100 maisons simulées" -ForegroundColor White
    Write-Host "  .\run.ps1 fleet 500          Lancer 500 maisons simulées" -ForegroundColor White
    Write-Host "  .\run.ps1 fleet 1000         Lancer 1000 maisons simulées" -ForegroundColor White
    Write-Host "  .\run.ps1 chaos              Test de résilience (bonus démo)" -ForegroundColor White
    Write-Host "  .\run.ps1 reset              Reset complet (efface les données)" -ForegroundColor White
    Write-Host ""
}

# --- Point d'entrée ---
Print-Header

switch ($Command.ToLower()) {
    "start"  { Start-Stack }
    "stop"   { Stop-Stack }
    "status" { Show-Status }
    "logs"   { Show-Logs -Service $Devices }
    "fleet"  { Start-Fleet -N $Devices }
    "reset"  { Reset-Stack }
    "chaos"  { Run-Chaos }
    "help"   { Show-Help }
    default  { Write-Host "❓ Commande inconnue. Utilise '.\run.ps1 help'" -ForegroundColor Red }
}
