import type { GameConcept, FileSpec, Genre } from './types'

// ── FILE TEMPLATES PER GENRE ──────────────────────────────────────────────────

const SHARED_FILES: FileSpec[] = [
  {
    path: 'ReplicatedStorage/GameConfig.lua',
    displayName: 'GameConfig',
    type: 'module',
    description: 'All game constants: resource defaults, zone definitions, spawn rates, upgrade costs, player defaults, gamepass IDs (use placeholder IDs like 000000001). Single source of truth for all tunable values. Include GAMEPASS_IDS table and DEVELOPER_PRODUCT_IDS table.',
    deps: [],
  },
  {
    path: 'ReplicatedStorage/RemoteEvents.lua',
    displayName: 'RemoteEvents',
    type: 'module',
    description: 'Creates and registers all RemoteEvents and RemoteFunctions in a Remotes folder under ReplicatedStorage. Returns a table with Get(name) helper. Include events for: resources, combat, building, notifications, mode selection, gamepass purchase prompts, shop purchases, daily rewards.',
    deps: [],
  },
  {
    path: 'ServerScriptService/DataManager.server.lua',
    displayName: 'DataManager',
    type: 'server',
    description: 'DataStore save/load with pcall and error logging. Auto-save every 60s via RunService.Heartbeat accumulator. newPlayerData() with ALL defaults including gamepasses, daily reward tracking, total playtime. Get/Set/Add/CanAfford/Deduct helpers. Data migration: if data.version < CURRENT_VERSION then migrate. Save on PlayerRemoving with 3s task.delay buffer.',
    deps: ['ReplicatedStorage/GameConfig.lua', 'ReplicatedStorage/RemoteEvents.lua'],
  },
  {
    path: 'ServerScriptService/GamepassManager.server.lua',
    displayName: 'GamepassManager',
    type: 'server',
    description: 'Monetization server script. On PlayerAdded: check UserOwnsGamePassAsync for VIP (2x income), AutoFarm (auto-collect), Speed (1.5x movement) gamepasses and apply their effects. Handle PromptPurchaseFinished to give immediate benefit. Handle ProcessReceipt for developer products: StarterPack (resource bundle), DoubleCoins30min (temporary buff), ExtraStorage (permanent upgrade). Apply multipliers to DataManager when player earns resources. Track active temporary buffs with expiry timestamps.',
    deps: ['ReplicatedStorage/GameConfig.lua', 'ReplicatedStorage/RemoteEvents.lua', 'ServerScriptService/DataManager.server.lua'],
  },
  {
    path: 'ServerScriptService/GameManager.server.lua',
    displayName: 'GameManager',
    type: 'server',
    description: 'Main server orchestrator. Handles PlayerAdded/Removing, loads DataManager and GamepassManager, sends resource updates to clients every 2 seconds via batched RemoteEvent, manages game state (lobby/playing/ended), GetLeaderboard RemoteFunction (top 10 by score), daily reward check on join (give bonus if first login today), session tracking for Premium payouts.',
    deps: ['ReplicatedStorage/GameConfig.lua', 'ReplicatedStorage/RemoteEvents.lua', 'ServerScriptService/DataManager.server.lua'],
  },
  {
    path: 'StarterGui/LoadingScreen.client.lua',
    displayName: 'LoadingScreen',
    type: 'client',
    description: 'Animated loading screen with game name, tagline, animated progress bar. Fades out when ContentProvider:PreloadAsync finishes. TweenService for smooth fade. Show tip text cycling through gameplay tips while loading.',
    deps: ['ReplicatedStorage/GameConfig.lua'],
  },
  {
    path: 'StarterGui/HUD.client.lua',
    displayName: 'HUD',
    type: 'client',
    description: 'Main HUD using UDim2 scale values (mobile-first). Resource display with TweenService animated counter on gain. Floating "+X" gain animations that rise and fade. Auto-save indicator (spinning icon that appears briefly). Daily reward notification popup. All TextScaled=true. Mobile-friendly touch targets (min 44px). ContextActionService for primary action button.',
    deps: ['ReplicatedStorage/GameConfig.lua', 'ReplicatedStorage/RemoteEvents.lua'],
  },
  {
    path: 'StarterGui/ShopGui.client.lua',
    displayName: 'ShopGui',
    type: 'client',
    description: 'Shop/gamepass UI panel. Two tabs: Gamepasses (VIP, AutoFarm, Speed) and Products (StarterPack, DoubleCoins30min). Each item shows icon, name, description, price in Robux, and OWNED badge if already purchased. Buy button calls MarketplaceService.PromptGamePassPurchase / PromptProductPurchase. Animated slide-in panel. Toggle with shop button on HUD.',
    deps: ['ReplicatedStorage/GameConfig.lua', 'ReplicatedStorage/RemoteEvents.lua'],
  },
  {
    path: 'StarterGui/LeaderboardGui.client.lua',
    displayName: 'LeaderboardGui',
    type: 'client',
    description: 'Toggleable leaderboard panel with 3 tabs (Score, Level, Rebirths). Polls GetLeaderboard RemoteFunction every 10s. Animated slide-in panel, sorted rows, current player row highlighted in cyan. Crown icon for #1.',
    deps: ['ReplicatedStorage/RemoteEvents.lua'],
  },
  {
    path: 'StarterPlayer/StarterPlayerScripts/PlayerController.client.lua',
    displayName: 'PlayerController',
    type: 'client',
    description: 'Player movement and input. ProximityPrompt for all world interactions (mobile compatible). Bridges ResourceUpdate RemoteEvent to HUD via BindableEvent. ContextActionService mobile action button for primary action. Respawn handling with camera reset. Speed multiplier application from GamepassManager buff.',
    deps: ['ReplicatedStorage/GameConfig.lua', 'ReplicatedStorage/RemoteEvents.lua'],
  },
]

const GENRE_FILES: Record<Genre, FileSpec[]> = {
  tycoon: [
    {
      path: 'ReplicatedStorage/Modules/ModuleData.lua',
      displayName: 'ModuleData',
      type: 'module',
      description: 'All buildable modules: id, displayName, cost, production rates, upgrade levels (5 tiers). Returns table with Get(id) and GetUpgradeCost(id, level) helpers.',
      deps: ['ReplicatedStorage/GameConfig.lua'],
    },
    {
      path: 'ServerScriptService/BaseManager.server.lua',
      displayName: 'BaseManager',
      type: 'server',
      description: 'Place/upgrade/remove modules in world. PlaceModule(player, moduleId, position, rotation), UpgradeModule(player, instanceId), RemoveModule. Validates cost via DataManager, creates Part with attributes, fires ModulePlaced/Upgraded/Removed events.',
      deps: ['ReplicatedStorage/RemoteEvents.lua', 'ReplicatedStorage/Modules/ModuleData.lua'],
    },
    {
      path: 'ServerScriptService/ResourceManager.server.lua',
      displayName: 'ResourceManager',
      type: 'server',
      description: 'AFK production loop via RunService.Heartbeat. calcProduction() sums all placed modules. Oxygen drain while diving. Food-to-coin conversion. MineNode(player, amount) for manual mining.',
      deps: ['ReplicatedStorage/GameConfig.lua', 'ReplicatedStorage/Modules/ModuleData.lua'],
    },
    {
      path: 'ServerScriptService/PrestigeSystem.server.lua',
      displayName: 'PrestigeSystem',
      type: 'server',
      description: 'Prestige system with 5 levels. CanPrestige check, DoPrestige resets base/resources but grants multiplier. FireClient notification on prestige. Prestige badge awards.',
      deps: ['ReplicatedStorage/RemoteEvents.lua'],
    },
    {
      path: 'StarterGui/BuildGui.client.lua',
      displayName: 'BuildGui',
      type: 'client',
      description: 'Build menu panel: category tabs, module cards with icon/cost/production stats, click to enter build mode. Ghost preview while placing. Confirmation on place. UpgradeGui popup on click of placed module.',
      deps: ['ReplicatedStorage/RemoteEvents.lua', 'ReplicatedStorage/Modules/ModuleData.lua'],
    },
    {
      path: 'StarterPlayer/StarterPlayerScripts/BuildingClient.client.lua',
      displayName: 'BuildingClient',
      type: 'client',
      description: 'Client-side build mode: ghost part preview on mouse, grid snap, rotation on R key, cancel on Escape, confirm on click. Sets _G.BuildingClient.IsInBuildMode(). Fires PlaceModule RemoteEvent.',
      deps: ['ReplicatedStorage/GameConfig.lua', 'ReplicatedStorage/RemoteEvents.lua'],
    },
  ],
  obby: [
    {
      path: 'ServerScriptService/CheckpointManager.server.lua',
      displayName: 'CheckpointManager',
      type: 'server',
      description: 'Checkpoint system: save last checkpoint per player, respawn at checkpoint on death, track stage number, award coins per new stage reached. CheckpointTouched RemoteEvent.',
      deps: ['ReplicatedStorage/RemoteEvents.lua'],
    },
    {
      path: 'ServerScriptService/StageManager.server.lua',
      displayName: 'StageManager',
      type: 'server',
      description: 'Stage progression: teleport to next stage area, track completion times, leaderboard by stage+time, award badges on milestone stages (10, 25, 50, 100).',
      deps: ['ReplicatedStorage/GameConfig.lua', 'ReplicatedStorage/RemoteEvents.lua'],
    },
    {
      path: 'StarterGui/StageGui.client.lua',
      displayName: 'StageGui',
      type: 'client',
      description: 'Stage progress display: current stage number, best time, checkpoint indicator. Animated stage complete popup with time and reward. Failure screen with respawn countdown.',
      deps: ['ReplicatedStorage/RemoteEvents.lua'],
    },
  ],
  simulator: [
    {
      path: 'ReplicatedStorage/Modules/PetData.lua',
      displayName: 'PetData',
      type: 'module',
      description: 'All pets: id, name, rarity (common/rare/epic/legendary), multiplier, model reference. GetRandom() with weighted rarity. GetMultiplier(petId) helper.',
      deps: [],
    },
    {
      path: 'ServerScriptService/CollectionManager.server.lua',
      displayName: 'CollectionManager',
      type: 'server',
      description: 'Collectible spawning and collection loop. Spawn collectible parts in zones, handle touch collection, award resources, respawn after delay. Area-of-effect collection via ProximityPrompt.',
      deps: ['ReplicatedStorage/GameConfig.lua', 'ReplicatedStorage/RemoteEvents.lua'],
    },
    {
      path: 'ServerScriptService/PetManager.server.lua',
      displayName: 'PetManager',
      type: 'server',
      description: 'Pet hatching from eggs (weighted random), equip/unequip pets, pet follows player via RunService, apply pet multipliers to collection. Max 3 equipped pets.',
      deps: ['ReplicatedStorage/Modules/PetData.lua', 'ReplicatedStorage/RemoteEvents.lua'],
    },
    {
      path: 'ServerScriptService/RebirtManager.server.lua',
      displayName: 'RebirthManager',
      type: 'server',
      description: 'Rebirth/prestige: check rebirth requirement (e.g., 1M coins), reset coins but grant permanent multiplier. Track rebirth count. Fire notification. Update leaderboard.',
      deps: ['ReplicatedStorage/RemoteEvents.lua'],
    },
    {
      path: 'StarterGui/SimulatorGui.client.lua',
      displayName: 'SimulatorGui',
      type: 'client',
      description: 'Main simulator UI: large resource counter with bounce animation on gain, egg hatching panel with animated reveal, pet inventory grid, rebirth button with requirement display, upgrade shop.',
      deps: ['ReplicatedStorage/RemoteEvents.lua'],
    },
  ],
  'battle-royale': [
    {
      path: 'ServerScriptService/MatchManager.server.lua',
      displayName: 'MatchManager',
      type: 'server',
      description: 'Match lifecycle: lobby countdown, teleport players to map, shrinking safe zone (kill players outside), track alive count, end match on 1 remaining, award winner. States: Lobby/Starting/Active/Ended.',
      deps: ['ReplicatedStorage/GameConfig.lua', 'ReplicatedStorage/RemoteEvents.lua'],
    },
    {
      path: 'ServerScriptService/LootManager.server.lua',
      displayName: 'LootManager',
      type: 'server',
      description: 'Loot spawn system: place weapon/supply crates across map at match start, handle ProximityPrompt pickup, give item to player inventory, despawn after pickup.',
      deps: ['ReplicatedStorage/GameConfig.lua', 'ReplicatedStorage/RemoteEvents.lua'],
    },
    {
      path: 'ServerScriptService/CombatManager.server.lua',
      displayName: 'CombatManager',
      type: 'server',
      description: 'Ranged and melee combat: raycast hit detection, damage application, kill tracking, headshot multiplier, death handling (drop loot, eliminate from match). ShootRemote from client.',
      deps: ['ReplicatedStorage/RemoteEvents.lua'],
    },
    {
      path: 'StarterGui/BattleHUD.client.lua',
      displayName: 'BattleHUD',
      type: 'client',
      description: 'Battle Royale HUD: health bar, shield bar, ammo counter, inventory slots (4 weapons), alive count, kill feed (last 5 kills), safe zone timer/shrink warning, win/loss screen.',
      deps: ['ReplicatedStorage/RemoteEvents.lua'],
    },
    {
      path: 'StarterPlayer/StarterPlayerScripts/WeaponController.client.lua',
      displayName: 'WeaponController',
      type: 'client',
      description: 'Weapon handling: equip/unequip on number keys, aim down sights on right-click, shoot raycast on left-click, recoil animation, reload system, muzzle flash VFX.',
      deps: ['ReplicatedStorage/RemoteEvents.lua'],
    },
  ],
  rpg: [
    {
      path: 'ReplicatedStorage/Modules/QuestData.lua',
      displayName: 'QuestData',
      type: 'module',
      description: 'All quests: id, title, description, objectives (kill X, collect Y, reach Z), rewards (XP, coins, item). GetByLevel(level) returns available quests.',
      deps: [],
    },
    {
      path: 'ServerScriptService/CombatManager.server.lua',
      displayName: 'CombatManager',
      type: 'server',
      description: 'Turn-based or action RPG combat: enemy AI, attack/dodge, damage calculation using player stats, status effects, loot drops on kill, XP rewards.',
      deps: ['ReplicatedStorage/RemoteEvents.lua'],
    },
    {
      path: 'ServerScriptService/QuestManager.server.lua',
      displayName: 'QuestManager',
      type: 'server',
      description: 'Quest tracking: AcceptQuest, UpdateProgress (called by combat/collection systems), CompleteQuest gives rewards, track active/completed quests in player data.',
      deps: ['ReplicatedStorage/Modules/QuestData.lua', 'ReplicatedStorage/RemoteEvents.lua'],
    },
    {
      path: 'StarterGui/RPGGui.client.lua',
      displayName: 'RPGGui',
      type: 'client',
      description: 'RPG UI: character stats panel (STR/DEF/SPD/LVL), quest journal with active/completed tabs, dialogue system for NPC interaction, loot popup on item pickup, level-up celebration.',
      deps: ['ReplicatedStorage/RemoteEvents.lua'],
    },
  ],
  shooter: [
    {
      path: 'ServerScriptService/CombatManager.server.lua',
      displayName: 'CombatManager',
      type: 'server',
      description: 'FPS/TPS combat: server-side raycast validation, damage with clamp, kill tracking, respawn system, team management, round win condition.',
      deps: ['ReplicatedStorage/RemoteEvents.lua'],
    },
    {
      path: 'StarterPlayer/StarterPlayerScripts/WeaponController.client.lua',
      displayName: 'WeaponController',
      type: 'client',
      description: 'Weapon system: shoot raycast, recoil, reload, ADS zoom, swap weapons, ammo HUD update.',
      deps: ['ReplicatedStorage/RemoteEvents.lua'],
    },
    {
      path: 'StarterGui/ShooterHUD.client.lua',
      displayName: 'ShooterHUD',
      type: 'client',
      description: 'Shooter HUD: crosshair, health bar, ammo count, kill feed, score display, round timer, team scores.',
      deps: ['ReplicatedStorage/RemoteEvents.lua'],
    },
  ],
  survival: [
    {
      path: 'ServerScriptService/SurvivalManager.server.lua',
      displayName: 'SurvivalManager',
      type: 'server',
      description: 'Survival mechanics: hunger/thirst/temperature drain over time, day/night cycle, weather system, death by starvation, resource gathering nodes. Heartbeat-based status drain.',
      deps: ['ReplicatedStorage/GameConfig.lua', 'ReplicatedStorage/RemoteEvents.lua'],
    },
    {
      path: 'ServerScriptService/CraftingManager.server.lua',
      displayName: 'CraftingManager',
      type: 'server',
      description: 'Crafting system: recipe table (input resources → output item), Craft(player, recipeId) validates inventory and produces item. Returns crafted item to player data.',
      deps: ['ReplicatedStorage/RemoteEvents.lua'],
    },
    {
      path: 'StarterGui/SurvivalHUD.client.lua',
      displayName: 'SurvivalHUD',
      type: 'client',
      description: 'Survival HUD: hunger bar (orange), thirst bar (blue), health bar (red), temperature gauge, day/night clock, inventory quick-access, crafting menu toggle.',
      deps: ['ReplicatedStorage/RemoteEvents.lua'],
    },
  ],
  racing: [
    {
      path: 'ServerScriptService/RaceManager.server.lua',
      displayName: 'RaceManager',
      type: 'server',
      description: 'Race lifecycle: countdown, checkpoint order validation (prevent skipping), lap tracking, finish detection, winner announcement, post-race rewards based on placement.',
      deps: ['ReplicatedStorage/GameConfig.lua', 'ReplicatedStorage/RemoteEvents.lua'],
    },
    {
      path: 'StarterGui/RaceHUD.client.lua',
      displayName: 'RaceHUD',
      type: 'client',
      description: 'Race HUD: current position (1st/2nd/3rd), lap counter, race timer, speed indicator, mini-map with player positions, finish banner with time and placement.',
      deps: ['ReplicatedStorage/RemoteEvents.lua'],
    },
  ],
  roleplay: [
    {
      path: 'ServerScriptService/RoleManager.server.lua',
      displayName: 'RoleManager',
      type: 'server',
      description: 'Role assignment: let players choose from available roles (chef, cashier, manager, customer, etc.). Track who has each role, enforce role limits (max 3 chefs at once). RoleChanged RemoteEvent. Spawn player at role-appropriate location. Save chosen role to DataManager.',
      deps: ['ReplicatedStorage/GameConfig.lua', 'ReplicatedStorage/RemoteEvents.lua'],
    },
    {
      path: 'ServerScriptService/InteractionManager.server.lua',
      displayName: 'InteractionManager',
      type: 'server',
      description: 'NPC and object interactions: serve customers, cook food, complete tasks. ProximityPrompt triggers, validate player role before allowing action, award coins on task complete, track reputation/score per player.',
      deps: ['ReplicatedStorage/RemoteEvents.lua'],
    },
    {
      path: 'StarterGui/RoleGui.client.lua',
      displayName: 'RoleGui',
      type: 'client',
      description: 'Role selection screen shown on join: grid of role cards with icon, name, description, current player count. Select role button. Current role display in HUD corner with switch button. Outfit/accessory preview per role.',
      deps: ['ReplicatedStorage/RemoteEvents.lua'],
    },
    {
      path: 'StarterGui/TaskGui.client.lua',
      displayName: 'TaskGui',
      type: 'client',
      description: 'Task/objective list panel: show current role tasks with progress bars (e.g. "Serve 3 customers: 1/3"), check off on completion, animated reward popup. Daily quest tracker. Reputation/rating display with star icons.',
      deps: ['ReplicatedStorage/RemoteEvents.lua'],
    },
  ],
  horror: [
    {
      path: 'ServerScriptService/HorrorManager.server.lua',
      displayName: 'HorrorManager',
      type: 'server',
      description: 'Horror game orchestrator: manages monster AI (patrol routes, detection radius, chase behavior), round phases (explore → monster spawns → escape). Monster catches player = out for round. Track survivors. Randomize monster spawn location each round. Sanity system: decrease when near monster, trigger hallucinations client-side at low sanity.',
      deps: ['ReplicatedStorage/GameConfig.lua', 'ReplicatedStorage/RemoteEvents.lua'],
    },
    {
      path: 'ServerScriptService/PuzzleManager.server.lua',
      displayName: 'PuzzleManager',
      type: 'server',
      description: 'Procedural puzzle placement: randomly place 5 puzzles across the map each round, track which players solved which. SolvePuzzle(player, puzzleId) validates and progresses escape. All puzzles solved = escape door opens. Puzzle types: switches, code locks, collectibles.',
      deps: ['ReplicatedStorage/RemoteEvents.lua'],
    },
    {
      path: 'StarterPlayer/StarterPlayerScripts/HorrorClient.client.lua',
      displayName: 'HorrorClient',
      type: 'client',
      description: 'Horror atmosphere client: heartbeat sound that increases with monster proximity (use Sound pitch/volume), screen vignette darkens near monster, screen shake on nearby footsteps, sanity visual distortion (blur, color shift via ColorCorrectionEffect), breathing heavy sound at low sanity. Jumpscare handler with screen flash.',
      deps: ['ReplicatedStorage/RemoteEvents.lua'],
    },
    {
      path: 'StarterGui/HorrorHUD.client.lua',
      displayName: 'HorrorHUD',
      type: 'client',
      description: 'Minimal horror HUD: sanity bar (top-right, white filling that drains), objective text (solve X puzzles, Y remaining), survivor count, proximity warning icon that pulses red when monster is near. Escape countdown when all puzzles solved. Round results (survived/caught) with spooky styling.',
      deps: ['ReplicatedStorage/RemoteEvents.lua'],
    },
  ],
  cozy: [
    {
      path: 'ServerScriptService/FarmManager.server.lua',
      displayName: 'FarmManager',
      type: 'server',
      description: 'Farming system: PlantSeed(player, plotId, seedType), GrowthLoop via RunService.Heartbeat (each crop has growthTime from GameConfig), HarvestCrop(player, plotId) gives resources, WaterCrop speeds growth by 2x. Unlockable plot expansion. Seasonal crops that only grow in certain weather. Save planted crops to DataManager with timestamp for offline growth calculation.',
      deps: ['ReplicatedStorage/GameConfig.lua', 'ReplicatedStorage/RemoteEvents.lua', 'ServerScriptService/DataManager.server.lua'],
    },
    {
      path: 'ServerScriptService/VillageManager.server.lua',
      displayName: 'VillageManager',
      type: 'server',
      description: 'Social village hub: track all player visits, TradeCrop(player, otherPlayer, cropId, amount) with both player confirmation, shared community garden that all players contribute to for bonus rewards, village reputation level unlocks new crops and decorations. Daily village event (e.g., harvest festival doubles sell prices).',
      deps: ['ReplicatedStorage/RemoteEvents.lua'],
    },
    {
      path: 'StarterGui/FarmGui.client.lua',
      displayName: 'FarmGui',
      type: 'client',
      description: 'Cozy farm UI: seed selection panel with cute icons, soil plot status (empty/planted/growing/ready), growth progress bar per plot, harvest button when ready with satisfying pop animation, shop panel to sell crops for coins, weather display (sunny/rainy/night cycle), seasonal decoration. Soft pastel color scheme.',
      deps: ['ReplicatedStorage/RemoteEvents.lua'],
    },
    {
      path: 'StarterGui/CatalogGui.client.lua',
      displayName: 'CatalogGui',
      type: 'client',
      description: 'Collection catalog: grid of all crop/item types with rarity star rating, shows how many the player has collected/total, animated sparkle on newly discovered items. Achievements panel: milestone rewards (grow 100 carrots, discover all rare crops). Farm decoration shop with cosmetic items.',
      deps: ['ReplicatedStorage/RemoteEvents.lua'],
    },
  ],
  cooking: [
    {
      path: 'ServerScriptService/KitchenManager.server.lua',
      displayName: 'KitchenManager',
      type: 'server',
      description: 'Cooking game server: recipe system (RECIPES table in GameConfig with ingredients + steps), CookDish(player, recipeId, ingredients) validates ingredients in inventory, starts cooking timer, returns completed dish. Order queue from NPC customers (OrderManager): random orders with time limit, fulfill order = coins + reputation, fail = reputation loss. Combo multiplier for consecutive correct orders.',
      deps: ['ReplicatedStorage/GameConfig.lua', 'ReplicatedStorage/RemoteEvents.lua', 'ServerScriptService/DataManager.server.lua'],
    },
    {
      path: 'ServerScriptService/IngredientManager.server.lua',
      displayName: 'IngredientManager',
      type: 'server',
      description: 'Ingredient system: ingredient nodes around kitchen that respawn every 30s, CollectIngredient(player, nodeId) adds to inventory, inventory slots limited (upgrade via gamepass), spoilage timer (ingredients expire after 5 minutes). Supply delivery events every 60s that give free ingredients. Track recipe completion for achievement system.',
      deps: ['ReplicatedStorage/RemoteEvents.lua'],
    },
    {
      path: 'StarterGui/KitchenGui.client.lua',
      displayName: 'KitchenGui',
      type: 'client',
      description: 'Cooking UI: active order tickets panel (Overcooked-style cards with dish icon, timer bar, tip amount), ingredient inventory grid, recipe book panel with all unlocked recipes and required ingredients, cooking station progress bar, combo counter display with fire animation at high combos, tips earned popup. Chaotic visual style with lots of color.',
      deps: ['ReplicatedStorage/RemoteEvents.lua'],
    },
    {
      path: 'StarterGui/RecipeBookGui.client.lua',
      displayName: 'RecipeBookGui',
      type: 'client',
      description: 'Recipe book: scrollable list of all recipes (locked ones show silhouette), click to see full recipe tree (ingredients → steps → final dish), visual ingredient icons, unlock requirement display, "Try Now" button that highlights required ingredients in inventory.',
      deps: ['ReplicatedStorage/RemoteEvents.lua'],
    },
  ],
  custom: [],
}

// ── PUBLIC API ─────────────────────────────────────────────────────────────────

export function getFileSpecs(concept: GameConcept): FileSpec[] {
  const genreFiles = GENRE_FILES[concept.genre] ?? []
  return [...SHARED_FILES, ...genreFiles]
}

export const PIPELINE_STEPS = [
  { id: 'analyze',  label: 'Analyzing concept',   description: 'Extracting genre, mechanics, systems' },
  { id: 'config',   label: 'Game Config',          description: 'Constants, zones, player defaults'   },
  { id: 'data',     label: 'Data Layer',           description: 'RemoteEvents, DataManager'            },
  { id: 'server',   label: 'Server Scripts',       description: 'GameManager, domain systems'          },
  { id: 'client',   label: 'Client Scripts',       description: 'HUD, PlayerController, UI'            },
  { id: 'rojo',     label: 'Rojo Config',          description: 'default.project.json'                 },
  { id: 'package',  label: 'Packaging',            description: 'Bundling into downloadable .zip'      },
]

export function stepIdForFile(spec: FileSpec): string {
  if (spec.path.includes('GameConfig')) return 'config'
  if (spec.path.includes('RemoteEvents') || spec.path.includes('DataManager')) return 'data'
  if (spec.type === 'server') return 'server'
  if (spec.type === 'client') return 'client'
  return 'server'
}
