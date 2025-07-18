import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import '../../../core/models/comment.dart';
import '../../settings/providers/settings_provider.dart';

class CommentWidget extends StatelessWidget {
  final Comment comment;
  final int depth;

  const CommentWidget({Key? key, required this.comment, this.depth = 0}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final settings = Provider.of<SettingsProvider>(context);
    final canDisplay = settings.replyDepthMax == -1 || depth <= settings.replyDepthMax;

    if (!canDisplay) {
      return Container();
    }

    return Card(
      margin: EdgeInsets.only(left: depth * 16.0, top: 8.0, right: 8.0),
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(12.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    comment.author,
                    style: Theme.of(context).textTheme.titleSmall,
                    overflow: TextOverflow.ellipsis, // Handles long names gracefully
                  ),
                ),
                if (settings.showUpvotes) ...[
                  const SizedBox(width: 8),
                  const Icon(Icons.arrow_upward, size: 16),
                  const SizedBox(width: 4),
                  Text(NumberFormat.compact().format(comment.ups)),
                ],
              ],
            ),
            if (settings.showTimestamp)
              Padding(
                padding: const EdgeInsets.only(top: 4.0),
                child: Text(
                  DateFormat.yMMMd().add_jms().format(comment.createdUtc),
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ),
            const SizedBox(height: 8),
            Text(comment.body),
            if (comment.replies.isNotEmpty)
              ListView.builder(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                itemCount: comment.replies.length,
                itemBuilder: (context, index) {
                  return CommentWidget(comment: comment.replies[index], depth: depth + 1);
                },
              ),
          ],
        ),
      ),
    );
  }
}

