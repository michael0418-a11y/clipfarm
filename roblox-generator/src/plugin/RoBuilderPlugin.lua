--[[
  RoBuilder AI Studio Plugin
  Install in Roblox Studio: Plugins > Plugin Manager > Install from file
  Requires: Your RoBuilder backend running at BACKEND_URL below

  HOW TO INSTALL:
  1. Run your RoBuilder backend (npm run dev in the roblox-generator folder)
  2. In Roblox Studio: Plugins tab > Plugin Manager > Install from file
  3. Select this .lua file
  4. The RoBuilder panel will appear on the right
--]]

-- ── CONFIG ────────────────────────────────────────────────────────────────────
local BACKEND_URL = "http://localhost:3000"  -- Change to your deployed URL for production
local PLUGIN_NAME = "RoBuilder AI"
local PLUGIN_VERSION = "1.0.0"

-- ── SERVICES ──────────────────────────────────────────────────────────────────
local HttpService    = game:GetService("HttpService")
local StudioService  = game:GetService("StudioService")
local Selection      = game:GetService("Selection")
local RunService     = game:GetService("RunService")

-- ── PLUGIN TOOLBAR ────────────────────────────────────────────────────────────
local toolbar      = plugin:CreateToolbar(PLUGIN_NAME)
local toggleButton = toolbar:CreateButton(
	"RoBuilder",
	"Open RoBuilder AI Panel",
	"rbxassetid://0"  -- Replace with a real icon asset ID if desired
)

-- ── WIDGET ────────────────────────────────────────────────────────────────────
local widgetInfo = DockWidgetPluginGuiInfo.new(
	Enum.InitialDockState.Right,
	true,   -- enabled by default
	false,  -- override previous state
	400,    -- default width
	650,    -- default height
	250,    -- min width
	400     -- min height
)

local widget = plugin:CreateDockWidgetPluginGui("RoBuilderWidget", widgetInfo)
widget.Title = PLUGIN_NAME

-- ── UI BUILDER ────────────────────────────────────────────────────────────────
local function makeFrame(parent, bg, size, pos, cornerRadius)
	local f = Instance.new("Frame")
	f.BackgroundColor3 = bg
	f.Size = size
	f.Position = pos or UDim2.new(0, 0, 0, 0)
	f.BorderSizePixel = 0
	f.Parent = parent
	if cornerRadius then
		local c = Instance.new("UICorner")
		c.CornerRadius = UDim.new(0, cornerRadius)
		c.Parent = f
	end
	return f
end

local function makeLabel(parent, text, size, pos, textColor, fontSize, bold)
	local l = Instance.new("TextLabel")
	l.Text = text
	l.Size = size
	l.Position = pos or UDim2.new(0, 0, 0, 0)
	l.TextColor3 = textColor or Color3.fromRGB(200, 200, 200)
	l.BackgroundTransparency = 1
	l.FontFace = Font.new(
		"rbxasset://fonts/families/GothamSSm.json",
		bold and Enum.FontWeight.Bold or Enum.FontWeight.Regular,
		Enum.FontStyle.Normal
	)
	l.TextSize = fontSize or 13
	l.TextXAlignment = Enum.TextXAlignment.Left
	l.TextWrapped = true
	l.Parent = parent
	return l
end

local function makeButton(parent, text, bg, textColor, size, pos, cornerRadius)
	local b = Instance.new("TextButton")
	b.Text = text
	b.Size = size
	b.Position = pos or UDim2.new(0, 0, 0, 0)
	b.BackgroundColor3 = bg
	b.TextColor3 = textColor
	b.BorderSizePixel = 0
	b.FontFace = Font.new("rbxasset://fonts/families/GothamSSm.json", Enum.FontWeight.Bold, Enum.FontStyle.Normal)
	b.TextSize = 13
	b.Parent = parent
	if cornerRadius then
		local c = Instance.new("UICorner")
		c.CornerRadius = UDim.new(0, cornerRadius)
		c.Parent = b
	end
	-- Hover effect
	b.MouseEnter:Connect(function()
		b.BackgroundColor3 = bg:Lerp(Color3.new(1, 1, 1), 0.1)
	end)
	b.MouseLeave:Connect(function()
		b.BackgroundColor3 = bg
	end)
	return b
end

local function makeInput(parent, placeholder, size, pos, multiLine)
	local box = Instance.new(multiLine and "TextBox" or "TextBox")
	box.PlaceholderText = placeholder
	box.Text = ""
	box.Size = size
	box.Position = pos or UDim2.new(0, 0, 0, 0)
	box.BackgroundColor3 = Color3.fromRGB(30, 30, 38)
	box.TextColor3 = Color3.fromRGB(220, 220, 220)
	box.PlaceholderColor3 = Color3.fromRGB(90, 90, 100)
	box.BorderSizePixel = 0
	box.FontFace = Font.new("rbxasset://fonts/families/RobotoMono.json")
	box.TextSize = 12
	box.TextXAlignment = Enum.TextXAlignment.Left
	box.TextYAlignment = multiLine and Enum.TextYAlignment.Top or Enum.TextYAlignment.Center
	box.MultiLine = multiLine or false
	box.TextWrapped = true
	box.ClearTextOnFocus = false
	local pad = Instance.new("UIPadding")
	pad.PaddingLeft = UDim.new(0, 10)
	pad.PaddingRight = UDim.new(0, 10)
	pad.PaddingTop = UDim.new(0, 8)
	pad.PaddingBottom = UDim.new(0, 8)
	pad.Parent = box
	local corner = Instance.new("UICorner")
	corner.CornerRadius = UDim.new(0, 6)
	corner.Parent = box
	local stroke = Instance.new("UIStroke")
	stroke.Color = Color3.fromRGB(60, 60, 75)
	stroke.Thickness = 1
	stroke.Parent = box
	box.Parent = parent
	return box
end

-- ── ROOT FRAME ────────────────────────────────────────────────────────────────
local root = makeFrame(widget,
	Color3.fromRGB(15, 15, 22),
	UDim2.new(1, 0, 1, 0)
)

local scrollFrame = Instance.new("ScrollingFrame")
scrollFrame.Size = UDim2.new(1, 0, 1, 0)
scrollFrame.BackgroundTransparency = 1
scrollFrame.ScrollBarThickness = 4
scrollFrame.ScrollBarImageColor3 = Color3.fromRGB(80, 80, 100)
scrollFrame.CanvasSize = UDim2.new(0, 0, 0, 0)
scrollFrame.AutomaticCanvasSize = Enum.AutomaticSize.Y
scrollFrame.Parent = root

local listLayout = Instance.new("UIListLayout")
listLayout.SortOrder = Enum.SortOrder.LayoutOrder
listLayout.Padding = UDim.new(0, 0)
listLayout.Parent = scrollFrame

local padding = Instance.new("UIPadding")
padding.PaddingLeft = UDim.new(0, 12)
padding.PaddingRight = UDim.new(0, 12)
padding.PaddingTop = UDim.new(0, 12)
padding.PaddingBottom = UDim.new(0, 12)
padding.Parent = scrollFrame

-- ── HEADER ────────────────────────────────────────────────────────────────────
local header = makeFrame(scrollFrame, Color3.fromRGB(20, 20, 30),
	UDim2.new(1, 0, 0, 56), nil, 10)
header.LayoutOrder = 1

local logo = makeFrame(header, Color3.fromRGB(0, 180, 220),
	UDim2.new(0, 32, 0, 32),
	UDim2.new(0, 10, 0.5, -16), 6)
makeLabel(logo, "R", UDim2.new(1, 0, 1, 0), nil, Color3.fromRGB(0, 0, 0), 16, true).TextXAlignment = Enum.TextXAlignment.Center

makeLabel(header, PLUGIN_NAME, UDim2.new(1, -60, 0, 20), UDim2.new(0, 52, 0, 8),
	Color3.fromRGB(255, 255, 255), 14, true)
makeLabel(header, "AI Game Developer v" .. PLUGIN_VERSION,
	UDim2.new(1, -60, 0, 16), UDim2.new(0, 52, 0, 28),
	Color3.fromRGB(100, 100, 120), 11)

-- ── TABS ──────────────────────────────────────────────────────────────────────
local tabBar = makeFrame(scrollFrame, Color3.fromRGB(20, 20, 28),
	UDim2.new(1, 0, 0, 38), nil, 0)
tabBar.LayoutOrder = 2

local tabLayout = Instance.new("UIListLayout")
tabLayout.FillDirection = Enum.FillDirection.Horizontal
tabLayout.SortOrder = Enum.SortOrder.LayoutOrder
tabLayout.Parent = tabBar

local TABS = {"Generate", "Chat", "Apply"}
local tabButtons = {}
local activeTab = "Generate"

for i, tabName in ipairs(TABS) do
	local btn = Instance.new("TextButton")
	btn.Text = tabName
	btn.Size = UDim2.new(0, 110, 1, 0)
	btn.BackgroundColor3 = Color3.fromRGB(20, 20, 28)
	btn.TextColor3 = Color3.fromRGB(120, 120, 140)
	btn.BorderSizePixel = 0
	btn.FontFace = Font.new("rbxasset://fonts/families/GothamSSm.json", Enum.FontWeight.SemiBold, Enum.FontStyle.Normal)
	btn.TextSize = 12
	btn.LayoutOrder = i
	btn.Parent = tabBar
	tabButtons[tabName] = btn
end

-- ── TAB PANELS ────────────────────────────────────────────────────────────────
local panels = {}

-- Generate Panel
local genPanel = makeFrame(scrollFrame, Color3.fromRGB(15, 15, 22),
	UDim2.new(1, 0, 0, 420), nil, 0)
genPanel.LayoutOrder = 3

local genLayout = Instance.new("UIListLayout")
genLayout.Padding = UDim.new(0, 10)
genLayout.Parent = genPanel

makeLabel(genPanel, "Describe your game:", UDim2.new(1, 0, 0, 16), nil,
	Color3.fromRGB(160, 160, 180), 12)

local descInput = makeInput(genPanel,
	"e.g. A cozy farming game where players grow crops, trade with friends, and unlock seasonal recipes",
	UDim2.new(1, 0, 0, 100), nil, true)

makeLabel(genPanel, "Quick examples:", UDim2.new(1, 0, 0, 14), nil,
	Color3.fromRGB(100, 100, 120), 11)

local exampleContainer = makeFrame(genPanel, Color3.fromRGB(15, 15, 22),
	UDim2.new(1, 0, 0, 130))
local exLayout = Instance.new("UIListLayout")
exLayout.Padding = UDim.new(0, 4)
exLayout.Parent = exampleContainer

local QUICK_EXAMPLES = {
	"Cozy farming village with trading",
	"Horror escape room with monster",
	"Underwater tycoon + prestige",
	"Cooking competition game",
}
for _, ex in ipairs(QUICK_EXAMPLES) do
	local exBtn = Instance.new("TextButton")
	exBtn.Text = "  " .. ex
	exBtn.Size = UDim2.new(1, 0, 0, 28)
	exBtn.BackgroundColor3 = Color3.fromRGB(25, 25, 35)
	exBtn.TextColor3 = Color3.fromRGB(140, 140, 160)
	exBtn.TextXAlignment = Enum.TextXAlignment.Left
	exBtn.FontFace = Font.new("rbxasset://fonts/families/GothamSSm.json")
	exBtn.TextSize = 11
	exBtn.BorderSizePixel = 0
	local c = Instance.new("UICorner"); c.CornerRadius = UDim.new(0, 5); c.Parent = exBtn
	exBtn.MouseButton1Click:Connect(function() descInput.Text = ex end)
	exBtn.Parent = exampleContainer
end

local genBtn = makeButton(genPanel, "🚀  Generate Full Game",
	Color3.fromRGB(0, 180, 220), Color3.fromRGB(0, 0, 0),
	UDim2.new(1, 0, 0, 40), nil, 8)

local genStatus = makeLabel(genPanel, "", UDim2.new(1, 0, 0, 50), nil,
	Color3.fromRGB(100, 100, 120), 11)
genStatus.TextWrapped = true

panels["Generate"] = genPanel

-- Chat Panel
local chatPanel = makeFrame(scrollFrame, Color3.fromRGB(15, 15, 22),
	UDim2.new(1, 0, 0, 420), nil, 0)
chatPanel.LayoutOrder = 3
chatPanel.Visible = false

local chatLayout2 = Instance.new("UIListLayout")
chatLayout2.Padding = UDim.new(0, 10)
chatLayout2.Parent = chatPanel

makeLabel(chatPanel, "Modify your game with AI:", UDim2.new(1, 0, 0, 16), nil,
	Color3.fromRGB(160, 160, 180), 12)

local chatDisplay = Instance.new("ScrollingFrame")
chatDisplay.Size = UDim2.new(1, 0, 0, 240)
chatDisplay.BackgroundColor3 = Color3.fromRGB(20, 20, 30)
chatDisplay.ScrollBarThickness = 4
chatDisplay.ScrollBarImageColor3 = Color3.fromRGB(80, 80, 100)
chatDisplay.CanvasSize = UDim2.new(0, 0, 0, 0)
chatDisplay.AutomaticCanvasSize = Enum.AutomaticSize.Y
chatDisplay.BorderSizePixel = 0
local cdCorner = Instance.new("UICorner"); cdCorner.CornerRadius = UDim.new(0, 8); cdCorner.Parent = chatDisplay
local cdPad = Instance.new("UIPadding")
cdPad.PaddingAll = UDim.new(0, 8); cdPad.Parent = chatDisplay
local cdLayout = Instance.new("UIListLayout"); cdLayout.Padding = UDim.new(0, 6); cdLayout.Parent = chatDisplay
chatDisplay.Parent = chatPanel

local chatInputBox = makeInput(chatPanel, "Ask to add a feature, fix a bug...",
	UDim2.new(1, 0, 0, 60), nil, true)

local chatSendBtn = makeButton(chatPanel, "Send →",
	Color3.fromRGB(0, 180, 220), Color3.fromRGB(0, 0, 0),
	UDim2.new(1, 0, 0, 36), nil, 8)

panels["Chat"] = chatPanel

-- Apply Panel
local applyPanel = makeFrame(scrollFrame, Color3.fromRGB(15, 15, 22),
	UDim2.new(1, 0, 0, 420), nil, 0)
applyPanel.LayoutOrder = 3
applyPanel.Visible = false

local applyLayout = Instance.new("UIListLayout")
applyLayout.Padding = UDim.new(0, 10)
applyLayout.Parent = applyPanel

makeLabel(applyPanel, "Paste Lua code to apply to Studio:", UDim2.new(1, 0, 0, 16), nil,
	Color3.fromRGB(160, 160, 180), 12)

local applyPathInput = makeInput(applyPanel, "Script path (e.g. ServerScriptService/GameManager)",
	UDim2.new(1, 0, 0, 36))

local applyCodeInput = makeInput(applyPanel, "Paste generated Lua code here...",
	UDim2.new(1, 0, 0, 200), nil, true)

local applyBtn = makeButton(applyPanel, "⬇  Apply to Studio",
	Color3.fromRGB(80, 200, 120), Color3.fromRGB(0, 0, 0),
	UDim2.new(1, 0, 0, 40), nil, 8)

local applyStatus = makeLabel(applyPanel, "Scripts are placed in ServerScriptService, StarterGui, etc. based on path prefix.",
	UDim2.new(1, 0, 0, 50), nil, Color3.fromRGB(100, 100, 120), 11)
applyStatus.TextWrapped = true

panels["Apply"] = applyPanel

-- ── TAB SWITCHING ─────────────────────────────────────────────────────────────
local function switchTab(tabName)
	activeTab = tabName
	for name, btn in pairs(tabButtons) do
		if name == tabName then
			btn.TextColor3 = Color3.fromRGB(0, 200, 240)
			btn.BackgroundColor3 = Color3.fromRGB(0, 60, 80)
		else
			btn.TextColor3 = Color3.fromRGB(120, 120, 140)
			btn.BackgroundColor3 = Color3.fromRGB(20, 20, 28)
		end
	end
	for name, panel in pairs(panels) do
		panel.Visible = (name == tabName)
	end
end

for _, tabName in ipairs(TABS) do
	tabButtons[tabName].MouseButton1Click:Connect(function()
		switchTab(tabName)
	end)
end
switchTab("Generate")

-- ── HELPER: Apply script to Studio ───────────────────────────────────────────
local function getOrCreateContainer(pathStr)
	-- pathStr: "ServerScriptService/GameManager.server" or "StarterGui/HUD.client"
	local parts = string.split(pathStr, "/")
	local serviceName = parts[1]

	local serviceMap = {
		ServerScriptService = game:GetService("ServerScriptService"),
		StarterGui          = game:GetService("StarterGui"),
		ReplicatedStorage   = game:GetService("ReplicatedStorage"),
		["StarterPlayer/StarterPlayerScripts"] = game:GetService("StarterPlayer"):FindFirstChild("StarterPlayerScripts"),
		StarterPlayer       = game:GetService("StarterPlayer"),
	}

	local parent = serviceMap[serviceName] or game:GetService(serviceName)
	if not parent then return nil, "Unknown service: " .. serviceName end

	-- Create intermediate folders if needed
	for i = 2, #parts - 1 do
		local existing = parent:FindFirstChild(parts[i])
		if not existing then
			local folder = Instance.new("Folder")
			folder.Name = parts[i]
			folder.Parent = parent
			parent = folder
		else
			parent = existing
		end
	end

	return parent, nil
end

local function applyScriptToStudio(pathStr, code)
	local fileName = string.split(pathStr, "/")[#string.split(pathStr, "/")]
	-- Detect script type from extension
	local scriptType = "ModuleScript"
	if string.find(fileName, "%.server") then
		scriptType = "Script"
		fileName = string.gsub(fileName, "%.server%.lua$", "")
		fileName = string.gsub(fileName, "%.server$", "")
	elseif string.find(fileName, "%.client") then
		scriptType = "LocalScript"
		fileName = string.gsub(fileName, "%.client%.lua$", "")
		fileName = string.gsub(fileName, "%.client$", "")
	else
		fileName = string.gsub(fileName, "%.lua$", "")
	end

	local parent, err = getOrCreateContainer(pathStr)
	if not parent then return false, err end

	-- Check if script already exists and update it
	local existing = parent:FindFirstChild(fileName)
	if existing and (existing:IsA("Script") or existing:IsA("LocalScript") or existing:IsA("ModuleScript")) then
		existing.Source = code
		return true, "Updated " .. fileName
	end

	-- Create new script
	local script = Instance.new(scriptType)
	script.Name = fileName
	script.Source = code
	script.Parent = parent

	return true, "Created " .. scriptType .. ": " .. fileName
end

-- ── GENERATE HANDLER ──────────────────────────────────────────────────────────
local generatedScripts = {}  -- cache: {path, content, displayName}

genBtn.MouseButton1Click:Connect(function()
	local desc = descInput.Text
	if #desc < 10 then
		genStatus.Text = "⚠ Please enter a longer description (at least 10 characters)."
		genStatus.TextColor3 = Color3.fromRGB(255, 160, 60)
		return
	end

	genBtn.Text = "⏳  Generating..."
	genBtn.BackgroundColor3 = Color3.fromRGB(60, 60, 80)
	genStatus.Text = "Connecting to RoBuilder AI..."
	genStatus.TextColor3 = Color3.fromRGB(100, 100, 120)
	generatedScripts = {}

	local ok, result = pcall(function()
		return HttpService:RequestAsync({
			Url = BACKEND_URL .. "/api/generate-sync",
			Method = "POST",
			Headers = { ["Content-Type"] = "application/json" },
			Body = HttpService:JSONEncode({ description = desc }),
		})
	end)

	if not ok then
		genStatus.Text = "❌ Connection failed. Is the RoBuilder server running at " .. BACKEND_URL .. "?"
		genStatus.TextColor3 = Color3.fromRGB(255, 80, 80)
		genBtn.Text = "🚀  Generate Full Game"
		genBtn.BackgroundColor3 = Color3.fromRGB(0, 180, 220)
		return
	end

	if result.StatusCode ~= 200 then
		genStatus.Text = "❌ Server error: " .. tostring(result.StatusCode)
		genStatus.TextColor3 = Color3.fromRGB(255, 80, 80)
		genBtn.Text = "🚀  Generate Full Game"
		genBtn.BackgroundColor3 = Color3.fromRGB(0, 180, 220)
		return
	end

	local data = HttpService:JSONDecode(result.Body)
	if data.files and #data.files > 0 then
		generatedScripts = data.files
		local applied = 0
		for _, f in ipairs(data.files) do
			local success, msg = applyScriptToStudio(f.path, f.content)
			if success then applied += 1 end
		end
		genStatus.Text = "✅ " .. #data.files .. " scripts generated, " .. applied .. " applied to Studio!\n\nGame: " .. (data.concept and data.concept.name or "Unknown") .. "\nSwitch to Chat tab to iterate."
		genStatus.TextColor3 = Color3.fromRGB(80, 220, 120)
	else
		genStatus.Text = "⚠ No files received from server."
		genStatus.TextColor3 = Color3.fromRGB(255, 160, 60)
	end

	genBtn.Text = "🚀  Generate Full Game"
	genBtn.BackgroundColor3 = Color3.fromRGB(0, 180, 220)
end)

-- ── CHAT HANDLER ─────────────────────────────────────────────────────────────
local chatHistory = {}  -- {role, text}

local function addChatMessage(role, text)
	local bubble = Instance.new("Frame")
	bubble.Size = UDim2.new(1, 0, 0, 0)
	bubble.AutomaticSize = Enum.AutomaticSize.Y
	bubble.BackgroundColor3 = role == "user"
		and Color3.fromRGB(0, 60, 80)
		or Color3.fromRGB(30, 30, 42)
	bubble.BorderSizePixel = 0
	local bc = Instance.new("UICorner"); bc.CornerRadius = UDim.new(0, 6); bc.Parent = bubble
	local bp = Instance.new("UIPadding")
	bp.PaddingLeft = UDim.new(0, 8); bp.PaddingRight = UDim.new(0, 8)
	bp.PaddingTop = UDim.new(0, 6); bp.PaddingBottom = UDim.new(0, 6); bp.Parent = bubble

	local prefix = role == "user" and "You: " or "AI: "
	local lbl = makeLabel(bubble, prefix .. text,
		UDim2.new(1, 0, 0, 0), nil,
		role == "user" and Color3.fromRGB(180, 230, 240) or Color3.fromRGB(200, 200, 210),
		11)
	lbl.AutomaticSize = Enum.AutomaticSize.Y
	lbl.Size = UDim2.new(1, 0, 0, 0)

	bubble.Parent = chatDisplay
	-- Scroll to bottom
	task.defer(function()
		chatDisplay.CanvasPosition = Vector2.new(0, chatDisplay.AbsoluteCanvasSize.Y)
	end)

	table.insert(chatHistory, { role = role, text = text })
end

chatSendBtn.MouseButton1Click:Connect(function()
	local msg = chatInputBox.Text
	if #msg < 2 then return end
	chatInputBox.Text = ""
	addChatMessage("user", msg)
	chatSendBtn.Text = "..."
	chatSendBtn.Active = false

	-- Build file context from cached scripts
	local filesPayload = {}
	for _, f in ipairs(generatedScripts) do
		table.insert(filesPayload, {
			path = f.path,
			displayName = f.displayName or f.path,
			type = f.type or "module",
			content = f.content,
			lines = #string.split(f.content, "\n"),
		})
	end

	local ok, result = pcall(function()
		return HttpService:RequestAsync({
			Url = BACKEND_URL .. "/api/chat",
			Method = "POST",
			Headers = { ["Content-Type"] = "application/json" },
			Body = HttpService:JSONEncode({
				message = msg,
				files = filesPayload,
				gameName = "My Roblox Game",
				gameGenre = "custom",
				coreLoop = "Play and have fun",
			}),
		})
	end)

	if not ok or result.StatusCode ~= 200 then
		addChatMessage("assistant", "❌ Error connecting to RoBuilder server.")
	else
		-- Parse SSE response for first 'text' or 'explanation' event
		local body = result.Body
		local responseText = ""
		for line in string.gmatch(body, "[^\n]+") do
			if string.sub(line, 1, 6) == "data: " then
				local raw = string.sub(line, 7)
				local ok2, ev = pcall(function() return HttpService:JSONDecode(raw) end)
				if ok2 and ev then
					if ev.type == "explanation" and ev.text then
						responseText = ev.text
					elseif ev.type == "text" and ev.text then
						responseText = ev.text
					elseif ev.type == "file" and ev.path and ev.content then
						applyScriptToStudio(ev.path, ev.content)
						-- Update cache
						for i, f in ipairs(generatedScripts) do
							if f.path == ev.path then
								generatedScripts[i].content = ev.content
								break
							end
						end
						if responseText == "" then
							responseText = "Updated: " .. ev.path
						end
					end
				end
			end
		end
		addChatMessage("assistant", responseText ~= "" and responseText or "Done.")
	end

	chatSendBtn.Text = "Send →"
	chatSendBtn.Active = true
end)

-- ── APPLY HANDLER ─────────────────────────────────────────────────────────────
applyBtn.MouseButton1Click:Connect(function()
	local pathStr = applyPathInput.Text
	local code    = applyCodeInput.Text
	if #pathStr < 3 or #code < 10 then
		applyStatus.Text = "⚠ Please fill in both the path and code."
		applyStatus.TextColor3 = Color3.fromRGB(255, 160, 60)
		return
	end

	local success, msg = applyScriptToStudio(pathStr, code)
	if success then
		applyStatus.Text = "✅ " .. msg
		applyStatus.TextColor3 = Color3.fromRGB(80, 220, 120)
		applyCodeInput.Text = ""
	else
		applyStatus.Text = "❌ " .. msg
		applyStatus.TextColor3 = Color3.fromRGB(255, 80, 80)
	end
end)

-- ── TOGGLE WIDGET ─────────────────────────────────────────────────────────────
toggleButton.Click:Connect(function()
	widget.Enabled = not widget.Enabled
end)

toggleButton.ClickableWhenViewportHidden = true
