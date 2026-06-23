#pragma once

namespace HudNavigation
{
    static constexpr int MAX_CHILDREN = 6;

    class State
    {
    public:
        const char *name;
        State *parent;
        State *children[MAX_CHILDREN];
        int childCount;
        int selectedIndex;

        State(const char *stateName)
            : name(stateName), parent(nullptr), childCount(0), selectedIndex(0)
        {
        }

        void addChild(State &child)
        {
            if (childCount >= MAX_CHILDREN)
            {
                return;
            }

            child.parent = this;
            children[childCount] = &child;
            childCount++;
        }

        bool hasChildren() const
        {
            return childCount > 0;
        }

        State *selectedChild()
        {
            if (!hasChildren())
            {
                return nullptr;
            }

            return children[selectedIndex];
        }
    };

    static State mainMenu("Menu");

    static State emotes("Emotes");
    static State settings("Settings");
    static State debug("Debug");

    static State emotesList("Emotes list");
    static State emotePreview("Emote preview");

    static State settingsWifi("WiFi");

    static State debugInfo("Debug info");
    static State debugLog("Debug log");

    static State *currentState = &mainMenu;

    static void begin()
    {
        mainMenu.addChild(emotes);
        mainMenu.addChild(settings);
        mainMenu.addChild(debug);

        emotes.addChild(emotesList);
        emotes.addChild(emotePreview);

        settings.addChild(settingsWifi);

        debug.addChild(debugInfo);
        debug.addChild(debugLog);

        currentState = &mainMenu;
    }

    static State &getState()
    {
        return *currentState;
    }

    static void moveUp()
    {
        if (!currentState->hasChildren())
        {
            return;
        }

        currentState->selectedIndex--;

        if (currentState->selectedIndex < 0)
        {
            currentState->selectedIndex = currentState->childCount - 1;
        }
    }

    static void moveDown()
    {
        if (!currentState->hasChildren())
        {
            return;
        }

        currentState->selectedIndex++;

        if (currentState->selectedIndex >= currentState->childCount)
        {
            currentState->selectedIndex = 0;
        }
    }

    static void select()
    {
        State *child = currentState->selectedChild();

        if (child != nullptr)
        {
            currentState = child;
        }
    }

    static void back()
    {
        if (currentState->parent != nullptr)
        {
            currentState = currentState->parent;
        }
    }
}
