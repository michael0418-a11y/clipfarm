-- LeaderboardGui.client.lua
-- Shows top players by Coins, Creatures Killed, and Depth Reached
-- Place in StarterGui as a LocalScript inside a ScreenGui named "LeaderboardGui"

local Players           = game:GetService("Players")
local TweenService      = game:GetService("TweenService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService        = game:GetService("RunService")

local Remotes = require(ReplicatedStorage:WaitForChild("RemoteEvents"))
local player  = Players.LocalPlayer
local gui     = script.Parent

-- ── LEADERBOARD REMOTE ────────────────────────────────────────────────────────
-- GetLeaderboard is created server-side in GameManager

-- ── PANEL ────────────────────────────────────────────────────────────────────

local panel            = Instance.new("Frame", gui)
panel.Name             = "LeaderboardPanel"
panel.Size             = UDim2.new(0, 320, 0, 400)
panel.Position         = UDim2.new(0, -330, 0.5, -200)
panel.BackgroundColor3 = Color3.fromRGB(5, 15, 45)
panel.BackgroundTransparency = 0.05
panel.ZIndex           = 20

local corner = Instance.new("UICorner", panel)
corner.CornerRadius = UDim.new(0, 12)

local stroke = Instance.new("UIStroke", panel)
stroke.Color = Color3.fromRGB(0, 180, 255)
stroke.Thickness = 2

-- Title bar
local titleBar         = Instance.new("Frame", panel)
titleBar.Size          = UDim2.new(1, 0, 0, 44)
titleBar.BackgroundColor3 = Color3.fromRGB(0, 80, 160)
titleBar.BorderSizePixel = 0
titleBar.ZIndex        = 21
local tbCorner         = Instance.new("UICorner", titleBar)
tbCorner.CornerRadius  = UDim.new(0, 12)

local titleLabel       = Instance.new("TextLabel", titleBar)
titleLabel.Size        = UDim2.new(1, 0, 1, 0)
titleLabel.BackgroundTransparency = 1
titleLabel.Text        = "🏆  LEADERBOARD"
titleLabel.TextColor3  = Color3.new(1, 1, 1)
titleLabel.TextScaled  = true
titleLabel.Font        = Enum.Font.GothamBold
titleLabel.ZIndex      = 22

-- Tab buttons
local tabs   = { "Coins", "Kills", "Depth" }
local tabBtns = {}
local activeTab = "Coins"

local tabBar = Instance.new("Frame", panel)
tabBar.Size  = UDim2.new(1, 0, 0, 34)
tabBar.Position = UDim2.new(0, 0, 0, 44)
tabBar.BackgroundTransparency = 1
tabBar.ZIndex = 21

for i, tabName in ipairs(tabs) do
	local btn            = Instance.new("TextButton", tabBar)
	btn.Name             = tabName
	btn.Size             = UDim2.new(1 / #tabs, 0, 1, 0)
	btn.Position         = UDim2.new((i - 1) / #tabs, 0, 0, 0)
	btn.BackgroundColor3 = Color3.fromRGB(10, 30, 70)
	btn.Text             = tabName
	btn.TextColor3       = Color3.fromRGB(150, 180, 220)
	btn.TextScaled       = true
	btn.Font             = Enum.Font.Gotham
	btn.BorderSizePixel  = 0
	btn.ZIndex           = 22
	tabBtns[tabName]     = btn
end

-- Scroll frame for rows
local scroll           = Instance.new("ScrollingFrame", panel)
scroll.Size            = UDim2.new(1, -10, 1, -90)
scroll.Position        = UDim2.new(0, 5, 0, 84)
scroll.BackgroundTransparency = 1
scroll.ScrollBarThickness = 4
scroll.CanvasSize      = UDim2.new(0, 0, 0, 0)
scroll.ZIndex          = 21

local layout           = Instance.new("UIListLayout", scroll)
layout.Padding         = UDim.new(0, 4)
layout.SortOrder       = Enum.SortOrder.LayoutOrder

-- ── ROW BUILDER ───────────────────────────────────────────────────────────────

local RANK_COLORS = {
	Color3.fromRGB(255, 215, 0),    -- gold
	Color3.fromRGB(200, 200, 200),  -- silver
	Color3.fromRGB(180, 100, 40),   -- bronze
}

local function clearRows()
	for _, c in ipairs(scroll:GetChildren()) do
		if c:IsA("Frame") then c:Destroy() end
	end
end

local function addRow(rank, name, value, unit)
	local row              = Instance.new("Frame", scroll)
	row.LayoutOrder        = rank
	row.Size               = UDim2.new(1, -8, 0, 44)
	row.BackgroundColor3   = rank % 2 == 0
		and Color3.fromRGB(12, 28, 65)
		or  Color3.fromRGB(8, 20, 50)
	row.BorderSizePixel    = 0
	row.ZIndex             = 22
	local rCorner          = Instance.new("UICorner", row)
	rCorner.CornerRadius   = UDim.new(0, 6)

	-- Rank number / medal
	local rankLabel        = Instance.new("TextLabel", row)
	rankLabel.Size         = UDim2.new(0, 40, 1, 0)
	rankLabel.BackgroundTransparency = 1
	rankLabel.Text         = rank <= 3 and ({ "🥇", "🥈", "🥉" })[rank] or "#" .. rank
	rankLabel.TextColor3   = RANK_COLORS[rank] or Color3.fromRGB(180, 180, 200)
	rankLabel.TextScaled   = true
	rankLabel.Font         = Enum.Font.GothamBold
	rankLabel.ZIndex       = 23

	-- Player name
	local nameLabel        = Instance.new("TextLabel", row)
	nameLabel.Size         = UDim2.new(0.5, 0, 1, 0)
	nameLabel.Position     = UDim2.new(0, 44, 0, 0)
	nameLabel.BackgroundTransparency = 1
	nameLabel.Text         = name
	nameLabel.TextColor3   = name == player.Name
		and Color3.fromRGB(100, 220, 255)
		or  Color3.fromRGB(200, 215, 230)
	nameLabel.TextScaled   = true
	nameLabel.Font         = name == player.Name and Enum.Font.GothamBold or Enum.Font.Gotham
	nameLabel.TextXAlignment = Enum.TextXAlignment.Left
	nameLabel.ZIndex       = 23

	-- Value
	local valueLabel       = Instance.new("TextLabel", row)
	valueLabel.Size        = UDim2.new(0.35, 0, 1, 0)
	valueLabel.Position    = UDim2.new(0.65, 0, 0, 0)
	valueLabel.BackgroundTransparency = 1
	valueLabel.Text        = tostring(value) .. " " .. unit
	valueLabel.TextColor3  = Color3.fromRGB(255, 215, 50)
	valueLabel.TextScaled  = true
	valueLabel.Font        = Enum.Font.Gotham
	valueLabel.TextXAlignment = Enum.TextXAlignment.Right
	valueLabel.ZIndex      = 23
end

-- ── POPULATE ─────────────────────────────────────────────────────────────────

local function populateTab(tab)
	clearRows()
	activeTab = tab

	-- Update tab button highlights
	for name, btn in pairs(tabBtns) do
		btn.BackgroundColor3 = name == tab
			and Color3.fromRGB(0, 100, 200)
			or  Color3.fromRGB(10, 30, 70)
		btn.TextColor3 = name == tab
			and Color3.new(1, 1, 1)
			or  Color3.fromRGB(150, 180, 220)
	end

	-- Fetch all players' public stats from server in one call
	local allData = Remotes.Get("GetLeaderboard"):InvokeServer()
	if not allData then allData = {} end

	local entries = {}
	for _, pdata in ipairs(allData) do
		local value = 0
		if tab == "Coins" then
			value = pdata.Coins or 0
		elseif tab == "Kills" then
			value = pdata.CreaturesKilled or 0
		elseif tab == "Depth" then
			value = pdata.Depth or 0
		end
		table.insert(entries, { name = pdata.name, value = value })
	end

	-- Sort descending
	table.sort(entries, function(a, b) return a.value > b.value end)

	local unit = tab == "Coins" and "💰" or tab == "Kills" and "☠" or "m"
	for i, entry in ipairs(entries) do
		addRow(i, entry.name, entry.value, unit)
	end

	layout:GetPropertyChangedSignal("AbsoluteContentSize"):Connect(function()
		scroll.CanvasSize = UDim2.new(0, 0, 0, layout.AbsoluteContentSize.Y + 8)
	end)
end

-- Tab click handlers
for _, tabName in ipairs(tabs) do
	tabBtns[tabName].Activated:Connect(function()
		populateTab(tabName)
	end)
end

-- ── TOGGLE BUTTON (top left) ──────────────────────────────────────────────────

local toggleBtn        = Instance.new("TextButton", gui)
toggleBtn.Name         = "LeaderboardToggle"
toggleBtn.Size         = UDim2.new(0, 44, 0, 44)
toggleBtn.Position     = UDim2.new(0, 10, 0.5, -200)
toggleBtn.BackgroundColor3 = Color3.fromRGB(0, 80, 160)
toggleBtn.Text         = "🏆"
toggleBtn.TextScaled   = true
toggleBtn.Font         = Enum.Font.GothamBold
toggleBtn.ZIndex       = 20
local tbCorner2        = Instance.new("UICorner", toggleBtn)
tbCorner2.CornerRadius = UDim.new(0, 10)

local isOpen = false

toggleBtn.Activated:Connect(function()
	isOpen = not isOpen
	if isOpen then
		populateTab("Coins")
		TweenService:Create(panel, TweenInfo.new(0.25, Enum.EasingStyle.Back), {
			Position = UDim2.new(0, 60, 0.5, -200),
		}):Play()
	else
		TweenService:Create(panel, TweenInfo.new(0.2), {
			Position = UDim2.new(0, -330, 0.5, -200),
		}):Play()
	end
end)

-- Refresh every 5 seconds when open
task.spawn(function()
	while true do
		task.wait(5)
		if isOpen then
			populateTab(activeTab)
		end
	end
end)
