task side bar display/editor does not alway update for every field that is editable on the expanded card. 

the animation between different views is still not that smooth. sometimes it stutters, sometimes it's smooth. opening and closing bubbles also does the same thing

It's really hard to read which project is which on the sidebar. The abbreviations don't really make it that legible. There should be a way to generate a unique icon for each project and have the name show up when we mouse over, just like for the overdue, upcoming, and all tasks. 

Creating a project feels lackluster, this is supposed to be something major, so it should have the visual weight of that. 

Checking off a task as complete also feels lackluster. This should be a moment of celebration.

We should have the redo/undo buttons work for non-ai edits as well, though we don't need to log them in the settings tab. 

The settings page needs to be redesigned, it's not organized enough currently. 

For the settings page, we should be able to change the label colors. There should be a way to auto generate descriptions for the labels via AI based on the current tasks with those labels

There should be ways to add more colors than the existing 8 in a nice UI friendly format

Deleting tasks should have a native UI popup rather than using the browser popup which feels jarring.

Deleting a project should be more involved, since this is a big change and we dont want to accidentally make this change. 

The filter button is persistent across all pages, which I'm not sure if that is right. It's even persistent in the settings menu where it doesn't do anything. we should redesign the positioning of the filter button and the search

The filter for labels should be condensed to a dropdown where we can select labels, and it should be able to take up multiple lines since right now we have too many labels

There's no way to delete labels. They should also autodelete if there are no tasks with them

When we filter, the UI is not very user friendly. There's no way to select/deselect multiple labels. There are also other things that we should filter for like due dates and subtasks

We need to bring back the icon indicators from the template where we indicate any attachments/subtasks. This is linked with the next issue

The cards/bubbles are too minimalistic, we should still have some icons that tell us important information about that task just from a glance. We also need to decide on what exactly we show when we hover over the card. Trello adds a checkoff circle when we hover over their cards. Are there pieces of info that would be relevant if we're just barely interested in the card or any ways to interact with the card that would follow our design philosophy and give users a better user experience?

There should be a little bit of an accent around the new though seed bubble, maybe the same color as the project color?

The drag and drop indicator is really unclear for the projects. Is it possible to render the dropped position while moving it? Maybe something similar to the cards in the kanban?

opening tasks in the kanban is broken since it tries to just expand the card. It should open the card in the viewer on the right. We also need to think about this workflow, since the viewer on the right takes up precious screen space which can display another kanban board. We'll need to think about the design of this deeper when we actually address this. 

The animation from list to bubbles/kanban is trippy because the cards display really big and shrink to their normal size. They should just fly in from the sidebar like normal. 

There should be a way to filter or something in the kanban columns. The information density is also not great, maybe we should make the cards smaller in the kanbans?

The kanban locations should also be reflected in the cards, either with a color tag or something else. A card that's in the To-Do column should be different in some way than a card that's in the Doing or Done column. The done column should also check the card off as complete.

The # completed button should have a hover effect to tell the user that it's interactive

I still don't love the positioning of the AI extract, maybe it should be on top or as a floating button on the bottom left or right?

There should be a way to control the max number of cards that's displayed or another view that shows the most important cards that need to be worked on in the all tasks page

There should be multiple ways to sort in the all tasks page. The default sort should take into account the due date and also when the task is set to be done. If the task is set to be done now or soon, it should put that task at the top. If a task doesn't have a set time to be done, but has a due date, it should be sorted by which ever due date is sooner, but also weighed by the priority, and also the length of time that the task will take. We should figure out a good algorithm for sorting

