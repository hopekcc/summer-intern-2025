# HopeKCC Summer Intern – Weekly Work Log

### Name: [Kishan Goli]
### Track: [Server]
### Week: [3]
### Date: [July 16th - July 21]
### Hour: [18]

---

## ✅ What's Done
- Worked through the room architecture/endpoints (create, join, leave, roomid, etc-)
- Integrated host ability to turn pages and send out to participants via websocket
- Setup the VM to work with the server (cannot authenticate as mentioned in blockers)

---

## 🔄 What's Active (with ETA)
- Work on ADMIN access, essentially restricting certain endpoints unless given certain permissions
- Fixing edge case with the room endpoint displaying the pdf to participants
- Batch Conversion
- Cleaning up endpoints
- CI/CD Pipeline
- Server officially run smoothly on VM

---

## ⏭️ What's Next
- Implement further endpoints and make sure it is tied into the database off-local. 
- Need to setup user's database and logging externally.
- Continue working with web/mobile team to ensure all calls are working as intended.

---

## 🛑 Blockers or Questions

- Blocker: Need to figure out the firebase situation. We are currently using a console that was created on my personal account, but for long term purposes, we will need to
move this over to a HopeKCC account if possible. We are still working on this console and are hoping we can just transfer ownership at the best case to a HopeKCC account.
Worst case we will have to do some manual transfering.

- Blocker: Github secrets. We currently have the server running live, but we need github secrets to hold our env code to actually test with this. Right now all our authentication fails because its not linked to our database users.

- Blocker: Access to each others VMs.

- Questions: No questions at the moment, seeing a lot of great progress as of now! :)


